import numpy as np
import gdal
import os
import glob
import ogr
import osr

from flask import current_app


TEMP_FLD = os.path.normpath("./processing/temp")
OUT_FLD_WGS = os.path.normpath('./data/aviable_cloud_masks/WGS84')
OUT_FLD = os.path.normpath('./data/aviable_cloud_masks/project')
IMG_FLD = os.path.normpath('./data/aviable_images') # relative from main.py

#current_app.logger.info(TEMP_FLD)

def s2to_numpy_stack(in_fld: str,
                   out_resolution=60,
                   temp_fld=TEMP_FLD) -> np.array:
    '''
    Take a folder with s2 image get
    jp2 images and stack it to np array
    params
    :param in_fld: folder with s2 imagery
    :out_resolution: out array resolution
    :temp_fld: temp folder for resample images
    '''

    opts = gdal.WarpOptions(
        xRes=out_resolution,
        yRes=out_resolution,
        #outputType=gdal.GDT_Int16
    )
    outArray = None

    # order 3 rd dimension
    order = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]

    filenames = list(glob.glob(os.path.join(IMG_FLD, in_fld, r"GRANULE\**\IMG_DATA\*B*.jp2")))

    # get order index based on position in order list from filename
    filenames.sort(key=lambda x: order.index(x.split('_')[-1][:3]))

    for filename in filenames:
        print(filename)
        ds = gdal.Open(filename)
        band = ds.GetRasterBand(1)
        if ds.GetGeoTransform()[1] != out_resolution:
            print(ds.GetGeoTransform()[1])
            tempRaster = os.path.join(temp_fld, "tempRaster.tif")
            gdal.Warp(tempRaster, filename, options=opts)
            dsTemp = gdal.Open(tempRaster)
            # print(np.max(dsTemp.ReadAsArray()))
            # IMPORTANT division by 10000 is necessary for normalize data
            normalizedArray = dsTemp.ReadAsArray() / 10000.0
            if outArray is None:
                outArray = normalizedArray
            else:
                outArray = np.dstack([outArray, normalizedArray])
            dsTemp = None
            # os.remove(tempRaster)
            continue
        else:
            normalizedArray = band.ReadAsArray() / 10000.0
            if outArray is None:
                outArray = normalizedArray
            else:
                outArray = np.dstack([outArray, normalizedArray])
        ds = None
        band = None
        dsTemp = None
    return outArray


def make_and_write_predict(inArray: np.array,
                           outPredictRaster: str,
                           WKID: int,
                           templateRasterPath: str
                           ) -> str:
    from s2cloudless import S2PixelCloudDetector
    cloud_detector = S2PixelCloudDetector(threshold=0.55, average_over=4, dilation_size=2, all_bands=True)
    cloud_masks = cloud_detector.get_cloud_masks(np.array([inArray]))


    # writing
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(WKID)
    ds: gdal.Dataset = gdal.Open(templateRasterPath)
    driver = gdal.GetDriverByName('GTiff')
    output_raster = driver.Create(
        outPredictRaster,
        cloud_masks[0].shape[0],
        cloud_masks[0].shape[0],
        1,
        gdal.GDT_Byte
    )
    output_raster.SetGeoTransform(ds.GetGeoTransform())
    output_raster.SetProjection(sr.ExportToWkt())
    output_raster.GetRasterBand(1).WriteArray(cloud_masks[0])
    output_raster.GetRasterBand(1).SetNoDataValue(0)
    output_raster.FlushCache()
    del output_raster
    ds = None


def polygonize_raster(inRaster, outGeoJSON: str, WKID: int):
    #sourceRaster = gdal.Open(inRaster, gdal.GA_Update)
    #band = sourceRaster.GetRasterBand(1)
    #band.SetNoDataValue(0.0)  # For polygonize only clouds
    #sourceRaster.GetRasterBand(1).
    #sourceRaster = None

    sourceRaster = gdal.Open(inRaster)
    band = sourceRaster.GetRasterBand(1)

    sr = osr.SpatialReference()
    sr.ImportFromEPSG(WKID)

    driver = ogr.GetDriverByName("GeoJSON")
    if os.path.exists(outGeoJSON):
        driver.DeleteDataSource(outGeoJSON)
    outDatasource = driver.CreateDataSource(outGeoJSON)
    outLayer = outDatasource.CreateLayer("mask", srs=sr)
    gdal.Polygonize(band, band, outLayer, -1, [], callback=None)
    outDatasource.Destroy()
    sourceRaster = None


def reproject_geojson(inSrc, outSrc, inWKID: int):

    driver = ogr.GetDriverByName("GeoJSON")

    # input SpatialReference
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(inWKID)

    # output SpatialReference
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)

    # create the CoordinateTransformation
    coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

    # get the input layer
    inDataSet = driver.Open(inSrc)
    inLayer = inDataSet.GetLayer()

    # create the output layer
    if os.path.exists(outSrc):
        driver.DeleteDataSource(outSrc)
    outDataSet = driver.CreateDataSource(outSrc)
    outLayer = outDataSet.CreateLayer("test", geom_type=ogr.wkbMultiPolygon, srs=outSpatialRef)

    # add fields
    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    # get the output layer's feature definition
    outLayerDefn = outLayer.GetLayerDefn()

    # loop through the input features
    inFeature = inLayer.GetNextFeature()
    while inFeature:
        # get the input geometry
        geom = inFeature.GetGeometryRef()
        # reproject the geometry
        geom.Transform(coordTrans)
        # create a new feature
        outFeature = ogr.Feature(outLayerDefn)
        # set the geometry and attribute

        # TODO in out layer flipped x and y temporary manually change order by SWAP
        geom.SwapXY()
        outFeature.SetGeometry(geom)
        for i in range(0, outLayerDefn.GetFieldCount()):
            outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
        # add the feature to the shapefile
        outLayer.CreateFeature(outFeature)
        # dereference the features and get the next input feature
        outFeature = None
        inFeature = inLayer.GetNextFeature()

    # Save and close the shapefiles
    inDataSet = None
    outDataSet = None

def get_wkid_from_fld(inFldPath:str)-> int:
    fldName = os.path.basename(inFldPath)
    tileID = fldName.split('_')[5]
    return 32600 + int(tileID[1:3])

def process_pipeline(inFld):
    # current_app.logger.info("Converting")
    inFldName = os.path.basename(inFld)
    #array_to_predict = s2to_numpy_stack(in_fld=inFld)

    # current_app.logger.info("Predicting cloud")
    WKID = get_wkid_from_fld(inFld)
    # # raster with 60 resolution
    #template = list(glob.glob(os.path.join(IMG_FLD, inFld, r"GRANULE\**\IMG_DATA\*B*.jp2")))[0]
    outRaster = os.path.join(TEMP_FLD, 'tempRaster.tif')
    #make_and_write_predict(array_to_predict, outRaster, WKID=WKID, templateRasterPath=template)

    # current_app.logger.info("Polygonize")
    outJSON = os.path.join(OUT_FLD, f'{inFldName}.geojson')
    polygonize_raster(outRaster, outJSON, WKID=WKID)

    current_app.logger.info("Projecting")
    outJSON_WGS = os.path.join(OUT_FLD_WGS, f'{inFldName}.geojson')
    reproject_geojson(outJSON, outJSON_WGS, inWKID=WKID)