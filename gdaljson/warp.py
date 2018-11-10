from gdaljson.projection import wkt
import copy
import functools
from pyproj import Proj, transform
from shapely.geometry import shape
from shapely.ops import transform as transform_geom
import math
import geojson
import json

class ArgumentError(BaseException):
    pass

def warp(in_vrt, dstSRS=None, height=None, width=None, xRes=None, yRes=None, resampleAlg="NearestNeighbour", warpMemoryLimit=64*1024*1024, dstAlpha=False, clipper=None, cropToCutline=False):
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
        "$": warpMemoryLimit
    },
        "ResampleAlg": {
            "$": resampleAlg
        },
        "WorkingDataType": {
            "$": workingvrt.bitdepth
        },
        "Option": [{
            "@name": "INIT_DEST",
            "$": "NO_DATA"
        }],
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
        #Update with new geotransform
        gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer']['DstGeoTransform']['$'] = ','.join([str(x) for x in gt])
        gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer']['DstInvGeoTransform']['$'] = ','.join([str(x) for x in inverse_geotransform(gt)])
        workingvrt.data['VRTDataset']['GeoTransform']['$'] = ','.join([str(x) for x in gt])
        workingvrt.data['VRTDataset']['@rasterXSize'] = cols
        workingvrt.data['VRTDataset']['@rasterYSize'] = rows


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

    if clipper:
        # Open the vector
        if hasattr(clipper, '__geo_interface__'):
            geom = shape(clipper)
        elif type(clipper) is str and clipper.endswith('.geojson'):
            geom = shape(geojson.load(open(clipper))['geometry'])
        elif type(clipper) is dict:
            geom = shape(geojson.load(json.dumps(clipper)))
        else:
            raise ValueError("Invalid clipper argument.")

        #Reproject geometry if image has been reprojected
        if dstSRS:
            project = functools.partial(transform, in_srs, out_srs)
            geom = transform_geom(project, geom)

        def coords_to_pix(x,y,z=None):
            return ((x - gt[0])/gt[1], (gt[3] - y)/-gt[5])

        # Calculate new GT and image size based on geometry
        bounds = geom.bounds
        if not cropToCutline:
            clip_gt = workingvrt.gt
        else:
            xsize, ysize = [int((bounds[2] - bounds[0]) / workingvrt.xres), int((bounds[3] - bounds[1]) / workingvrt.yres)]
            clip_gt = [bounds[0], (bounds[2] - bounds[0]) / xsize, 0, bounds[3], 0, -((bounds[3] - bounds[1]) / ysize)]

            workingvrt.data['VRTDataset']['@rasterXSize'] = xsize
            workingvrt.data['VRTDataset']['@rasterYSize'] = ysize
            workingvrt.data['VRTDataset']['GeoTransform']['$'] = ','.join([str(x) for x in clip_gt])

            #Adjust blocksize
            if min(in_vrt.blocksize) < min(xsize, ysize):
                workingvrt.data['VRTDataset']['BlockXSize'] = {'$': xsize}
                workingvrt.data['VRTDataset']['BlockYSize'] = {'$': ysize}
            else:
                workingvrt.data['VRTDataset']['BlockXSize'] = {'$': in_vrt.blocksize[0]}
                workingvrt.data['VRTDataset']['BlockYSize'] = {'$': in_vrt.blocksize[1]}

        gdalwarp_opts['Cutline'] = {'$': transform_geom(coords_to_pix, geom).to_wkt()}
        gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer']['DstGeoTransform']['$'] = ','.join([str(x) for x in clip_gt])
        gdalwarp_opts['Transformer']['ApproxTransformer']['BaseTransformer']['GenImgProjTransformer']['DstInvGeoTransform']['$'] = ','.join([str(x) for x in inverse_geotransform(clip_gt)])


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

    if dstAlpha:
        #Alpha band options
        workingvrt.data['VRTDataset']['VRTRasterBand'].append({'@dataType': in_vrt.bitdepth,
                                                                '@band': in_vrt.shape[2]+1,
                                                                '@subClass': 'VRTWarpedRasterBand',
                                                                'ColorInterp': {
                                                                    '$': 'Alpha'
                                                                }})
        gdalwarp_opts['DstAlphaBand'] = {'$': workingvrt.shape[2]}
        gdalwarp_opts['Option'].append({'@name': 'DST_ALPHA_MAX', '$': 32767})
        gdalwarp_opts['Option'][0]['$'] = 0

        #Removing nodata values from rest of VRT
        for item in gdalwarp_opts['BandList']['BandMapping']:
            del(item['DstNoDataReal'])
            del(item['DstNoDataImag'])
        allowed = ['ColorInterp', '@dataType', '@band', '@subClass', 'VRTRasterBand']
        for d in workingvrt.data['VRTDataset']['VRTRasterBand']:
            for (k,v) in dict(d).items():
                if k not in allowed:
                    del(d[k])
    workingvrt.data['VRTDataset']['GDALWarpOptions'] = gdalwarp_opts
    return workingvrt


def inverse_geotransform(gt):
    inverse = [-(gt[0] / gt[1]), 1 / gt[1], 0, gt[3] / gt[1], 0, 1 / gt[5]]
    return inverse