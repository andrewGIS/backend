import numpy as np
import gdal
import os
import glob
import ogr
import osr

from flask import current_app


TEMP_FLD = os.path.join(current_app.instance_path, os.path.normpath("processing/temp"))
OUT_FLD_WGS = os.path.join(current_app.instance_path, os.path.normpath('data/aviable_cloud_masks/WGS84'))
OUT_FLD = os.path.join(current_app.instance_path, os.path.normpath('data/aviable_cloud_masks/project'))

current_app.logger.info(TEMP_FLD)

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


    opts = gdal.WarpOptions(xRes=out_resolution, yRes=out_resolution)
    outArray = None

    # order 3 rd dimension
    order = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]

    filenames = [filename for filename in glob.glob(os.path.join(in_fld, r"\**\IMG_DATA\*B*.jp2"), recursive=True)]
    # get order index based on position in order list from filename
    filenames.sort(key=lambda x: order.index(x.split('_')[-1][:3]))

    for filename in filenames:
        print(filename)
        ds = gdal.Open(filename)
        if ds.GetGeoTransform()[1] != out_resolution:
            print(ds.GetGeoTransform()[1])
            ds = None
            tempRaster = os.path.join(temp_fld, "tempRaster.tif")
            gdal.Warp(tempRaster, filename, options=opts)
            ds = gdal.Open(tempRaster)
            normalizedArray = (ds.ReadAsArray() /
                               ds.GetRasterBand(1).GetStatistics(True, True)[1])
            if outArray is None:
                outArray = normalizedArray
            else:
                outArray = np.dstack([outArray, normalizedArray])
            ds = None
            os.remove(tempRaster)
            continue
        else:
            normalizedArray = (ds.ReadAsArray() /
                               ds.GetRasterBand(1).GetStatistics(True, True)[1])
            if outArray is None:
                outArray = normalizedArray
            else:
                outArray = np.dstack([outArray, normalizedArray])
                ds = None
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
    output_raster = (gdal.GetDriverByName('GTiff').Create(f'../scratch/{outPredictRaster}',
                                                          cloud_masks[0].shape[0],
                                                          cloud_masks[0].shape[0],
                                                          1,
                                                          gdal.GDT_Float32))
    output_raster.SetGeoTransform(ds.GetGeoTransform())
    output_raster.SetProjection(sr.ExportToWkt())
    output_raster.GetRasterBand(1).WriteArray(cloud_masks[0])
    output_raster.FlushCache()
    del output_raster
    ds = None



def polygonize_raster(inRaster, outFolder: str, outGeoJSON: str):
    outShapefile = os.path.basename(inRaster).split(".tif")[0]
    out = os.path.join(outFolder, outGeoJSON)
    if os.path.exists(out):
        return
        # driver.DeleteDataSource(outShapefile)
    sourceRaster = gdal.Open(inRaster, gdal.GA_Update)

    band = sourceRaster.GetRasterBand(1)
    band.SetNoDataValue(0.0)  # For polygonize only clouds
    band = sourceRaster.GetRasterBand(1)

    driver = ogr.GetDriverByName("GeoJSON")
    if os.path.exists(out):
        driver.DeleteDataSource(outShapefile)
    outDatasource = driver.CreateDataSource(out)
    outLayer = outDatasource.CreateLayer(out, srs=None)
    gdal.Polygonize(band, None, outLayer, -1, [], callback=None)
    # gdal.Polygonize(band, None, outLayer, 0, [], callback=None )
    outDatasource.Destroy()
    inRaster = None

def reproject_geojson(inSrc, outSrc, inWKID:int):

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
    output = outSrc
    if os.path.exists(output):
        driver.DeleteDataSource(output)
    outDataSet = driver.CreateDataSource(output)
    outLayer = outDataSet.CreateLayer("mask", geom_type=ogr.wkbMultiPolygon)

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

def get_wkid_from_fld(inFldPath:str)-> int:
    fldName = os.path.basename(inFldPath)
    tileID = fldName.split('_')[5]
    return 32600 + int(tileID[1:3])

def process_pipeline(inFld):
    inFldName = os.path.basename(inFld)
    array_to_predict = s2to_numpy_stack(in_fld=inFld)

    current_app.logger.info("Processing")
    WKID = get_wkid_from_fld(inFld)
    template = [filename for filename in glob.glob(
        os.path.join(inFld, r"\**\IMG_DATA\*B11.jp2"), recursive=True
    )][0]
    outRaster = os.path.join(TEMP_FLD, 'tempRaster.tif')
    make_and_write_predict(array_to_predict, outRaster, WKID=WKID, templateRasterPath=template)

    current_app.logger.info("Processing1")
    outJSON = os.pah.join(OUT_FLD, f'{inFldName}.geojson')
    polygonize_raster(outRaster, TEMP_FLD, outJSON)

    current_app.logger.info("Processing2")
    outJSON_WGS = os.pah.join(OUT_FLD_WGS, f'{inFldName}.geojson')
    reproject_geojson(outJSON, outJSON_WGS, inWKID=WKID)