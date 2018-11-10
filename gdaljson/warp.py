from gdaljson.projection import wkt
import copy
from pyproj import Proj, transform
import math

class ArgumentError(BaseException):
    pass

def warp(in_vrt, dstSRS=None, height=None, width=None, xRes=None, yRes=None, resampleAlg="NearestNeighbor"):
    workingvrt = copy.deepcopy(in_vrt)
    fname = workingvrt.filename
    gt = copy.deepcopy(in_vrt.gt)

    #Convert to warped vrt
    workingvrt.data['VRTDataset']['@subClass'] = "VRTWarpedDataset"
    for i in range(in_vrt.shape[2]):
        workingvrt.data['VRTDataset']['VRTRasterBand'][i]['@subClass'] = 'VRTWarpedRasterBand'
        #Deleve the source
        del(workingvrt.data['VRTDataset']['VRTRasterBand'][i][workingvrt.source])

    #Setup default gdalwarp options
    gdalwarp_opts = {"WarpMemoryLimit": {
        "$": 67108900.0
    },
        "ResampleAlg": {
            "$": resampleAlg
        },
        "WorkingDataType": {
            "$": workingvrt.bitdepth
        },
        "Option": {
            "@name": "INIT_DEST",
            "$": "NO_DATA"
        },
        "SourceDataset": {
            "@relativeToVRT": 0,
            "$": fname
        },
        "Transformer": {
            "ApproxTransformer": {
                "MaxError": {
                    "$": 0.125
                },
                "BaseTransformer": {
                    "GenImgProjTransformer": {
                        "SrcGeoTransform": {
                            "$": in_vrt.data['VRTDataset']['GeoTransform']['$']
                        },
                        "SrcInvGeoTransform": {
                            "$": ','.join([str(x) for x in inverse_geotransform(in_vrt.gt)])
                        },
                        "DstGeoTransform": {
                            "$": in_vrt.data['VRTDataset']['GeoTransform']['$']
                        },
                        "DstInvGeoTransform": {
                            "$": ','.join([str(x) for x in inverse_geotransform(in_vrt.gt)])
                        }
                    }
                }
            }
        },
        "BandList": {
            "BandMapping": []
    }
    }

    if dstSRS:
        extent = in_vrt.extent
        out_wkt = wkt(dstSRS)
        workingvrt.data['VRTDataset']['SRS']['$'] = out_wkt
        in_srs = Proj(init=f'epsg:{in_vrt.epsg}')
        out_srs = Proj(init=f'epsg:{dstSRS}')

        # Calculate new resolution (see https://www.gdal.org/gdal__alg_8h.html#a816819e7495bfce06dbd110f7c57af65)
        # Resolution is computed with the intent that the length of the distance from the top left corner of the output
        # imagery to the bottom right corner would represent the same number of pixels as in the source image
        source_pixels_diag = math.sqrt(in_vrt.shape[0]**2 + in_vrt.shape[1]**2)
        proj_tl = transform(in_srs, out_srs, extent[0], extent[3])
        proj_br = transform(in_srs, out_srs, extent[1], extent[2])
        projwidth = (proj_br[0] - proj_tl[0])
        projheight = (proj_tl[1] - proj_br[1])
        projdiag = math.sqrt(projwidth**2 + projheight**2)
        res = projdiag / source_pixels_diag

        #Calculate new cols and rows based on res
        cols = round(projwidth / res)
        rows = round(projheight / res)

        gt[0] = proj_tl[0]
        gt[1] = res
        gt[3] = proj_tl[1]
        gt[5] = -res



        #Update transformer
        transformer = {"ReprojectTransformer": {
                        "ReprojectionTransformer": {
                            "SourceSRS": {
                                "$": in_vrt.srs.wkt
                                },
                            "TargetSRS": {
                                 "$": out_wkt
                                }
                            }
                        }}
        gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer'].update(transformer)

    for i in range(workingvrt.shape[2]):
        gdalwarp_opts['BandList']['BandMapping'].append({"@src": i+1,
                                                         "@dst": i+1,
                                                         "SrcNoDataReal": {
                                                             "$": workingvrt.nodata
                                                         },
                                                         "SrcNoDataImag": {
                                                             "$": 0
                                                         },
                                                         "DstNoDataReal": {
                                                             "$": workingvrt.nodata
                                                         },
                                                         "DstNoDataImag": {
                                                             "$": 0
                                                         }
                                                         })
    #Update with new geotransform
    gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer']['DstGeoTransform']['$'] = ','.join([str(x) for x in gt])
    gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer']['DstInvGeoTransform']['$'] = ','.join([str(x) for x in inverse_geotransform(gt)])
    workingvrt.data['VRTDataset']['GeoTransform']['$'] = ','.join([str(x) for x in gt])
    workingvrt.data['VRTDataset']['@rasterXSize'] = cols
    workingvrt.data['VRTDataset']['@rasterYSize'] = rows


    workingvrt.data['VRTDataset']['GDALWarpOptions'] = gdalwarp_opts

    if height or width:
        if (height or width) and (xRes or yRes):
            raise ArgumentError("height/width and xRes/yRes are mutually exclusive")
        if height and width:
            _height = height
            _width = width
        else:
            if height:
                ratio = workingvrt.shape[1] / height
                _width = int(round(workingvrt.shape[0] / ratio))
                _height = height
            elif width:
                ratio = workingvrt.shape[0] / width
                _height = int(workingvrt.shape[1] / ratio)
                _width = width

        gt[1] = (gt[1] * workingvrt.shape[0]) / _width  # (extent of image) / new width
        gt[5] = (gt[5] * workingvrt.shape[1]) / _height
        workingvrt.data['VRTDataset']['@rasterXSize'] = _width
        workingvrt.data['VRTDataset']['@rasterYSize'] = _height

    elif xRes and yRes:
        ratiox = workingvrt.xres * workingvrt.shape[0]
        ratioy = workingvrt.yres * workingvrt.shape[1]
        _width = int(round(ratiox / xRes))
        _height = int(round(ratioy / yRes))

        gt[1] = xRes
        gt[5] = -yRes
        workingvrt.data['VRTDataset']['@rasterXSize'] = _width
        workingvrt.data['VRTDataset']['@rasterYSize'] = _height


    return workingvrt


def inverse_geotransform(gt):
    inverse = [-(gt[0] / gt[1]), 1 / gt[1], 0, gt[3] / gt[1], 0, 1 / gt[5]]
    return inverse