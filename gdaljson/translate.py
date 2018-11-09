import copy

class ArgumentError(BaseException):
    pass

def translate(input_vrt, bandList=None, srcWin=None, projWin=None, height=None, width=None, xRes=None, yRes=None, nodata=None):

    """JSON encoded wrapper of gdal.Translate"""

    workingvrt = copy.deepcopy(input_vrt)
    source = workingvrt.source
    gt = copy.deepcopy(workingvrt.gt)

    #Handle bands first
    if bandList:
        bands = [[workingvrt.data['VRTDataset']['VRTRasterBand'][i-1] for i in bandList]][0]
        workingvrt.data['VRTDataset']['VRTRasterBand'] = bands
        #Update band ordering
        [workingvrt.data['VRTDataset']['VRTRasterBand'][i].update({'@band': i+1}) for i in range(workingvrt.shape[2])]

    if srcWin or projWin:
        if srcWin and projWin:
            raise ArgumentError("srcWin and projWin are mutually exlusive")
        if projWin:
            xoff, yoff = [int((projWin[0] - workingvrt.tlx) / workingvrt.xres),
                          int((workingvrt.tly - projWin[1]) / workingvrt.yres)]
            xsize, ysize = [int((projWin[2] - projWin[0]) / workingvrt.xres),
                            int((projWin[1] - projWin[3]) / workingvrt.yres)]
            srcWin = [xoff, yoff, xsize, ysize]
        workingvrt.update_src_rect(srcWin)
        workingvrt.update_dst_rect([0,0,srcWin[2],srcWin[3]])

    if height or width:
        if (height or width) and (xRes or yRes):
            raise ArgumentError("height/width and xRes/yRes are mutually exclusive")
        if height and width:
            workingvrt.update_dst_rect([0,0,width,height])
            _width = width
            _height = height
        else:
            if height:
                #If just height is given, calculate matching width.
                ratio = workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@ySize'] / height
                _width = int(workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@xSize'] / ratio)
                _height = height
            elif width:
                #If just width is given, calculate matching height
                ratio = workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@xSize'] / width
                _height = int(workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@ySize'] / ratio)
                _width = width
            workingvrt.update_dst_rect([0,0,_width,_height])
        #Calculate new resolution based on new dimensions
        gt[1] = (workingvrt.xres * workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@xSize']) / _width
        gt[5] = -(workingvrt.yres * workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@ySize']) / _height

    elif xRes and yRes:
        ratiox = workingvrt.xres * workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@xSize']
        ratioy = workingvrt.yres * workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@ySize']
        #Calculate new width and height based on input resolution
        _width = int(ratiox / xRes)
        _height = int(ratioy / yRes)
        workingvrt.update_dst_rect([0,0,_width,_height])
        gt[1] = xRes
        gt[5] = -yRes

    #Fix geotransform and image dimensions based on changes to DstRect
    gt[0] = workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@xOff'] * workingvrt.xres + workingvrt.tlx
    gt[3] = workingvrt.tly - workingvrt.data['VRTDataset']['VRTRasterBand'][0][source]['SrcRect']['@yOff'] * workingvrt.yres
    workingvrt.data['VRTDataset']['GeoTransform']['$'] = ','.join([str(x) for x in gt])

    #Update raster size to match bands
    workingvrt.data['VRTDataset']['@rasterXSize'] = workingvrt.bandshape[0]
    workingvrt.data['VRTDataset']['@rasterYSize'] = workingvrt.bandshape[1]

    if nodata:
        workingvrt.nodata = nodata
    return workingvrt