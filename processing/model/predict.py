
from typing import List
import glob
import datetime
from tensorflow import keras
from skimage import io

# TODO install 3.3.0 gdal version
try:
    from osgeo import osr
    from osgeo import ogr
    from osgeo import gdal
except ImportError:
    import osr
    import ogr
    import gdal

import os
import numpy as np

from ..clouds.make_cloud_mask import process_pipeline

import config

from ..utils import (
    get_raster_size,
    get_raster_resolution,
    get_raster_extent,
    get_raster_projection,
    get_bands,
    check_rasters_list,
    get_raster_path,
    polygonize_raster,
    reproject_geojson,
    get_wkid_from_fld
)

TEMP_WARP_FLD = config.TEMP_WARP_FLD
TEMP_STACK_FLD = config.TEMP_STACK_FLD
TEMP_TILES_FLD = config.TEMP_TILES_FLD
TEMP_PREDICT_FLD = config.TEMP_PREDICT_FLD
STATIC_FLD = config.STATIC_FLD
IMG_FLD = config.IMG_FLD
OUT_PATH = config.OUT_PREDICT_FLD
OUT_PATH_WGS = config.OUT_PREDICT_FLD_WGS
OUT_CLOUD_FLD = config.OUT_CLOUD_FLD
OUT_FILTERED = config.OUT_PREDICT_FLD_FILTERED


def stack_layers(sampleFld: str,
                 oldList: List,
                 newList: List,
                 outFld: str,
                 outName: str,
                 features_count: int = 16,
                 res: int = 20
                 ):
    """
    Stack layers in one raster (now of the same resolution)
    and calculate difference

    :param res: spatial resolution
    :param sampleFld:str folder with original images (old or new) used for get information about raster
    :param oldList: band list from first image expected in order B04, B08, B11, B12
    :param newList: band list from first image expected in order B04, B08, B11, B12
    :param inputRasterPathsList: input init rasters for model
    :param outFld:
    :param outName:
    :param features_count: Number of input feature for model predict
    :return:
    """

    # sample_raster = oldList[0]
    if res == 60:
        sample_raster = get_raster_path(sampleFld, "B01", IMG_FLD)
    if res == 20:
        sample_raster = get_raster_path(sampleFld, "B05", IMG_FLD)
    if res == 10:
        sample_raster = get_raster_path(sampleFld, "B04", IMG_FLD)

    x_ncells, y_ncells = get_raster_size(sample_raster)
    cellsize = get_raster_resolution(sample_raster)

    x_min, x_max, y_min, y_max = get_raster_extent(sample_raster)
    output_tiff = os.path.join(outFld, outName)

    # create output (spatial ref from first raster)
    out_driver = gdal.GetDriverByName('GTiff')
    out_source = out_driver.Create(
        output_tiff,
        x_ncells,
        y_ncells,
        8,
        gdal.GDT_UInt16
    )
    out_source.SetGeoTransform((x_min, cellsize, 0, y_max, 0, -cellsize))
    out_source.SetProjection(get_raster_projection(newList[0]))

    # TODO refactor this make more simpler
    idx_map = [
        [1, 2],  # B04
        # [new channel index, old channel index, new - old dif index, old - new dif index]
        [3, 4],  # B08
        [5, 6],  # B11
        [7, 8]  # B12
    ]

    # writing original data
    # indexes of new channel in out raster
    for oldRaster, newRaster, idxs in zip(oldList, newList, idx_map):
        # new_idx, old_idx, dif1_idx, dif2_idx = idxs
        new_idx, old_idx = idxs
        old = gdal.Open(oldRaster).ReadAsArray()
        new = gdal.Open(newRaster).ReadAsArray()
        # dif1 = new - old
        # dif2 = old - new

        out_source.GetRasterBand(old_idx).WriteArray(old)
        out_source.GetRasterBand(new_idx).WriteArray(new)
        # out_source.GetRasterBand(dif1_idx).WriteArray(dif1)
        # out_source.GetRasterBand(dif2_idx).WriteArray(dif2)

        old = None
        new = None

    out_source = None

    return output_tiff


def raster2tile(inRaster, outFolder, tileSize=256, res: int = 10):
    """
    Split raster to chunks (512 to 512)
    """

    if res == 10:
        width = 10980
        height = 10980

    if res == 20:
        width = 5490
        height = 5490

    if res == 60:
        width = 1830
        height = 1830

    for i in range(0, width, tileSize):
        for j in range(0, height, tileSize):
            opts = gdal.TranslateOptions(
                format="GTiff",
                srcWin=[i, j, tileSize, tileSize],
            )

            gdal.Translate(os.path.join(outFolder, f"tile_{i}_{j}.tif"), inRaster, options=opts)


def merge_tiles(inFld, outFile):
    """
    Merge all predicted tiles to one file
    :param inFld: folder with predicted tiles
    :param outFile: merged geotiff file with extension
    :return:
    """
    lsTfs = list(glob.glob(f'{inFld}/*.tif'))

    bltOpts = gdal.BuildVRTOptions()
    ds = gdal.BuildVRT('mosaic.vrt', lsTfs, options=bltOpts)

    outDs = gdal.GetDriverByName("GTiff").Create(
        outFile,
        ds.RasterXSize,
        ds.RasterYSize,
        1,
        gdal.GDT_Float32
    )

    predict_limit = 0.1
    rawArray = ds.ReadAsArray().astype(np.float32)
    filteredArray = np.where(rawArray > predict_limit, rawArray, -9999.0)

    outDs.GetRasterBand(1).WriteArray(filteredArray)
    outDs.GetRasterBand(1).SetNoDataValue(-9999.0)
    srsSpRef = ds.GetSpatialRef()

    outDs.SetProjection(srsSpRef.ExportToWkt())
    outDs.SetGeoTransform(ds.GetGeoTransform())

    ds = None
    outDs = None

    if os.path.exists('mosaic.vrt'):
        os.remove('mosaic.vrt')


def predict_folder(
        model_path='./files/winterBackboneFirstTest.h5',
        inFld='../../ds/ds_validation_256_256_26/L1C_T40VEM_A024828_20200324T073608_L1C_T40VEM_A014132_20191120T074121/',
        outFld='/home/andrew.tarasov1993.gmail.com/outs/geoRefPredict'
               '/L1C_T40VEM_A024828_20200324T073608_L1C_T40VEM_A014132_20191120T074121'
):
    model = keras.models.load_model(model_path, compile=False)

    print(datetime.datetime.now())
    for img in os.listdir(inFld):
        # print (img)

        if img.endswith('.tif'):
            inImg = os.path.join(inFld, img)
            outTile = os.path.join(outFld, img)
            tileSize = 256

            # rasterArray = gdal_array.LoadFile(np.array(inImg))

            arr = io.imread(inImg) / 65536
            # print(rasterArray.shape)
            # if rasterArray.shape[0] != 256 or rasterArray.shape[1] != 256:
            #     # print (f"{img} - incorrect shape")
            #     rasterArray = None
            #     continue

            # print(inImg)
            # srcDs = gdal.Open(inImg)

            b4new = arr[:, :, 0]
            b4old = arr[:, :, 1]
            b8new = arr[:, :, 2]
            b8old = arr[:, :, 3]
            b11new = arr[:, :, 4]
            b11old = arr[:, :, 5]
            b12new = arr[:, :, 6]
            b12old = arr[:, :, 7]

            # TODO check features order and calculation
            toPredict = np.array(
                np.dstack([
                    b4new,
                    b8new,
                    b4old,
                    b8old,
                    b4new - b4old,
                    b4old - b4new,
                    b8new - b8old,
                    b8old - b8new,
                    b12new,
                    b12old,
                    b12new - b12old,
                    b12old - b12new,
                    b11new,
                    b11old,
                    b11new - b11old,
                    b11old - b11new,
                ]).astype('float32'))

            testPrediction = model.predict(np.array([toPredict]))

            srcDs = gdal.Open(inImg)
            driver = gdal.GetDriverByName("GTiff")
            srsSpRef = srcDs.GetSpatialRef()

            dstDs = driver.Create(outTile, tileSize, tileSize, 1, gdal.GDT_Float32)
            dstDs.SetProjection(srsSpRef.ExportToWkt())
            dstDs.SetGeoTransform(srcDs.GetGeoTransform())

            dstDs.GetRasterBand(1).WriteArray(testPrediction[0][:, :, 0].astype(np.float32))
            # dstDs.FlushCache()
            dstDs = None
            src = None
    print(datetime.datetime.now())

def erase(in_layer, erase_layers: List, out_ds, WKID):

    #TODO optimizsing process

    srcDs = ogr.Open(in_layer)
    srcLayer = srcDs.GetLayer()
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(WKID)
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)
    coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    outDriver = ogr.GetDriverByName('GeoJSON')
    if os.path.exists(out_ds):
        outDriver.DeleteDataSource(out_ds)
    outDataSource = outDriver.CreateDataSource(out_ds)
    outLayer: ogr.Layer = outDataSource.CreateLayer('predict', geom_type=ogr.wkbMultiPolygon, srs=outSpatialRef)

    for feature in srcLayer:
        needDestroy = False
        feature_out: ogr.Feature = ogr.Feature(outLayer.GetLayerDefn())
        feature_out.SetGeometry(feature.GetGeometryRef())
        for erase_layer in erase_layers:
            erDs = ogr.Open(erase_layer)
            eLayer = erDs.GetLayer()
            for f1 in eLayer:
                eraseGeom: ogr.Geometry = f1.GetGeometryRef()
                #TODO check it
                if not f1:
                    continue
                if eraseGeom.Contains(feature_out.geometry()):
                    needDestroy = True
                    break

                erased: ogr.Geometry = feature_out.GetGeometryRef().Difference(eraseGeom)
                #erased: ogr.Geometry = feature_out.geometry().MakeValid().Difference(eraseGeom)

                # TODO check it
                if not erased:
                    continue
                feature_out.SetGeometry(erased)
            erDs = None
            eLayer = None

        # if predict object inside cloud
        if needDestroy:
            feature_out.Destroy()
            continue

        feature_out.GetGeometryRef().Transform(coordTrans)
        feature_out.GetGeometryRef().SwapXY()
        if feature_out.GetGeometryRef().IsEmpty():
            feature_out.Destroy()
            continue
        outLayer.CreateFeature(feature_out)
        feature_out.Destroy()

    outDataSource.Destroy()
    srcDs = None


# @celery.task()
def predict_pipeline(oldImg, newImg, warpFolder=TEMP_WARP_FLD, stackFolder=TEMP_STACK_FLD, resolution=10):
    # s2 bands
    # ["B01","B02","B03","B04","B05","B06","B07","B08","B8A","B09","B10","B11","B12"]

    featuresOld = get_bands(oldImg, ["B04", "B08", "B11", "B12"],
                            imgFolder=IMG_FLD)

    featuresNew = get_bands(newImg, ["B04", "B08", "B11", "B12"],
                            imgFolder=IMG_FLD)
    # print (featuresOld,'\n',featuresNew)
    print("Resolution checking")
    checkedRastersOld = check_rasters_list(featuresOld, resolution, warpFolder)
    checkedRastersNew = check_rasters_list(featuresNew, resolution, warpFolder)

    print("Stacking")
    outStack = os.path.join(stackFolder, f'{oldImg}_{newImg}.tif')
    if not os.path.exists(outStack):
        outStack = stack_layers(sampleFld=oldImg, oldList=checkedRastersOld, newList=checkedRastersNew,
                                outFld=TEMP_STACK_FLD, outName=f'{oldImg}_{newImg}.tif', res=resolution)

    rasterName = os.path.basename(outStack).split('.tif')[0]
    tilesFolderPath = os.path.join(TEMP_TILES_FLD, rasterName)

    print("Tiling")
    if not os.path.exists(tilesFolderPath):
        os.mkdir(tilesFolderPath)
        raster2tile(outStack, tilesFolderPath, 256, res=resolution)

    print("Predict")
    model = os.path.join(STATIC_FLD, "AllMyUnet_36.h5")
    outPredictPath = os.path.join(TEMP_PREDICT_FLD, rasterName)
    if not os.path.exists(outPredictPath):
        os.mkdir(outPredictPath)
        predict_folder(model, tilesFolderPath, outPredictPath)

    print("Merge predict")
    outRaster = os.path.join(TEMP_PREDICT_FLD, rasterName + '.tif')
    if not os.path.exists(outRaster):
        merge_tiles(outPredictPath, outRaster)

    print("Polygomize predict")
    WKID = get_wkid_from_fld(oldImg)
    outJSON = os.path.join(OUT_PATH, rasterName + '.geojson')
    if not os.path.exists(outJSON):
        polygonize_raster(outRaster, outJSON, WKID)

    print("Project predict")
    outJSON_WGS = os.path.join(OUT_PATH_WGS, rasterName + '.geojson')
    if not os.path.exists(outJSON_WGS):
        reproject_geojson(outJSON, outJSON_WGS, WKID)

    print("Cloud filtering")
    oldImgMask = os.path.join(OUT_CLOUD_FLD, oldImg + '.geojson')
    if not os.path.exists(oldImgMask):
        process_pipeline(oldImg)

    newImgMask = os.path.join(OUT_CLOUD_FLD, newImg + '.geojson')
    if not os.path.exists(newImgMask):
        process_pipeline(newImg)

    outFilteredJSON = os.path.join(OUT_FILTERED, rasterName + '.geojson')
    erase(outJSON, [oldImgMask, newImgMask], outFilteredJSON, WKID)
