import os
import gdal
import glob
import ogr
import osr
import io
from PIL import Image
import base64

#TODO make config in one file
IMG_FLD = os.path.normpath('./data/aviable_images')  # relative from main.py
TEMP_PARTS_FLD = os.path.normpath("./processing/temp/img_parts")


def get_raster_size(rasterPath):
    """
    Get raster size in pixel
    """
    infoOptions = gdal.InfoOptions(format='json')
    return gdal.Info(rasterPath, options=infoOptions)['size']


def get_raster_resolution(rasterPath):
    """
    Get raster pixel size
    """
    infoOptions = gdal.InfoOptions(format='json')
    return gdal.Info(rasterPath, options=infoOptions)["geoTransform"][1]


def get_raster_extent(rasterPath):
    """
    Get raster extent
    """

    infoOptions = gdal.InfoOptions(format='json')
    infoResult = gdal.Info(rasterPath, options=infoOptions)
    # return as -te <xmin> <ymin> <xmax> <ymax>
    return ((infoResult["cornerCoordinates"]['lowerLeft'])
            + (infoResult["cornerCoordinates"]['upperRight']))


def get_raster_projection(rasterPath):
    """
    Get raster projection
    """

    infoOptions = gdal.InfoOptions(format='json')
    infoResult = gdal.Info(rasterPath, options=infoOptions)
    # return as -te <xmin> <ymin> <xmax> <ymax>
    return infoResult["coordinateSystem"]['wkt']


def get_raster_path(imgFld,
                  channelTemplate="B08",
                  allImgFld=r"../addDataUsedImgs/"):
    """
    Get raster path of template channel
    """

    findString = os.path.normpath(f'''{allImgFld}//{imgFld}//**//*{channelTemplate}.jp2''')
    #print(findString)
    findResults = glob.glob(findString, recursive=True)

    if len(findResults) != 1:
        raise ValueError(f'Template raster shoud be uniq or exists!, not {len(findResults)}')

    return findResults[0]


def get_bands(inputFld, bandsList, imgFolder='./'):
    """
    Return list of raster path to neccesary bands
    """
    avialableBands = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]

    outPaths = []
    for channel in bandsList:
        if channel not in avialableBands:
            ValueError(f'Channel {channel} not exists !')
        outPaths.append(get_raster_path(inputFld, channelTemplate=channel, allImgFld=imgFolder))

    return outPaths



def raster2tile(inRaster, outFolder, tileSize=512):
    """
    Split raster to chunks (512 to 512)
    """
    import subprocess

    if not os.path.exists(outFolder):
        os.mkdir(outFolder)

    print(" ".join([
        '"/home/gis/anaconda3/envs/geoTools/bin/python"',
        '"/home/gis/anaconda3/envs/geoTools/bin/gdal_retile.py"',
        f' -ps {tileSize} {tileSize}',
        f' -targetDir "{os.path.normpath(outFolder)}"',
        f' "{os.path.normpath(inRaster)}"'
    ]))
    subprocess.call(
        " ".join([
            '"/home/gis/anaconda3/envs/geoTools/bin/python"',
            '"/home/gis/anaconda3/envs/geoTools/bin/gdal_retile.py"',
            f' -ps {tileSize} {tileSize}',
            f' -targetDir "{os.path.normpath(outFolder)}"',
            f' "{os.path.normpath(inRaster)}"'
        ]),
        shell=True
    )


def resample_raster(inRaster, outRaster, outResolution):
    """
    Resample raster to other spatial resolution
    """
    warpOptions = gdal.WarpOptions(xRes=outResolution, yRes=outResolution)
    # TODO check that resolution are equals in other case delete wrapped layer
    if os.path.exists(outRaster):
        return outRaster
    gdal.Warp(outRaster, inRaster, options=warpOptions)

    return outRaster


def check_rasters_list(inputList, targetResolution, wrapFld):
    """
    Check resolution for all rasters in list
    If resolution are other wrap it
    and replace data in list
    """
    for index, raster in enumerate(inputList):
        if not get_raster_resolution(raster) == targetResolution:
            print("Find raster with other resolution, warp")
            rasterName = os.path.basename(raster).replace('.jp2', '.tif')
            outRaster = os.path.join(wrapFld, rasterName)
            # if os.path.exists(outRaster):
            #     inputList[index] = outRaster
            #     continue
            resampledRaster = resample_raster(raster, outRaster, targetResolution)
            inputList[index] = outRaster
    return inputList


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


def get_pixel_type(rasterPath):
    """
    Get raster type of pixel by first band (used type in my app 'UInt16', 'Byte')
    """
    infoOptions = gdal.InfoOptions(format='json')
    return gdal.Info(rasterPath, options=infoOptions)['bands'][0]['type']

def get_subset_from_image(inFldName: str, channelName: str,
                          xmin: float, xmax: float, ymin: float, ymax:float) -> str:
    rasterPath = get_raster_path(inFldName, channelName, IMG_FLD)
    WKID = get_wkid_from_fld(inFldName)

    # input SpatialReference
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(4326)

    # output SpatialReference
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(WKID)

    # create the CoordinateTransformation
    coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

    #bottomLeft = ogr.CreateGeometryFromWkt(f"POINT ({xmin} {ymin})")
    bottomLeft = ogr.CreateGeometryFromWkt(f"POINT ({ymin} {xmin})")
    #upperRight = ogr.CreateGeometryFromWkt(f"POINT ({xmax} {ymax})")
    upperRight = ogr.CreateGeometryFromWkt(f"POINT ({ymax} {xmax})")

    bottomLeft.Transform(coordTrans)
    upperRight.Transform(coordTrans)

    outImg = os.path.join(TEMP_PARTS_FLD, f'{inFldName}.bmp')

    pixelType = get_pixel_type(rasterPath)
    if pixelType == 'Byte':
        optsWarp = gdal.WarpOptions(
            outputBounds=[
                bottomLeft.GetX(),  # xmin
                bottomLeft.GetY(),  # ymin
                upperRight.GetX(),  # xmax
                upperRight.GetY()   # ymax
            ],
            outputType=gdal.GDT_Byte
        )
        result = gdal.Warp(outImg, rasterPath, options=optsWarp)
        result = None

    if pixelType == 'UInt16':
        # For display in bmp need to scale value
        # Translate projWin not working coordinates in Wrap
        tempTif = outImg.replace('.bmp', '.tif')
        optsWarp = gdal.WarpOptions(
            outputBounds=[
                bottomLeft.GetX(),  # xmin
                bottomLeft.GetY(),  # ymin
                upperRight.GetX(),  # xmax
                upperRight.GetY()  # ymax
            ],
            outputType=gdal.GDT_UInt16
        )
        result = gdal.Warp(tempTif, rasterPath, options=optsWarp)
        result = None

        ds = gdal.Open(tempTif)
        band = ds.GetRasterBand(1)
        # maxValue = band.GetMaximum()
        # minValue = band.GetMinimum()
        minValue, maxValue = band.ComputeRasterMinMax()
        # return jsonify({'test': 'test'})
        optsTranslate = gdal.TranslateOptions(
            outputBounds=[
                bottomLeft.GetX(),  # xmin
                bottomLeft.GetY(),  # ymin
                upperRight.GetX(),  # xmax
                upperRight.GetY()  # ymax
            ],
            scaleParams=[[0, maxValue, 0, 255]],
            outputType=gdal.GDT_Byte
        )
        result = gdal.Translate(outImg, tempTif, options=optsTranslate)
        band = None
        ds = None
        result = None

    return outImg








