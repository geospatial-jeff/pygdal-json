import json
from osgeo import gdal
from xmljson import badgerfish as bf
import xml.etree.ElementTree as ET
import xml.dom.minidom as md

from gdaljson.projection import SpatialRef
from gdaljson.transformations import loads

class Raster(object):

    def __init__(self, vrt):
        if type(vrt) is dict:
            self.data = vrt
        else:
            self.data = loads(vrt)
        try:
            self.srs = SpatialRef(self.data['VRTDataset']['SRS']['$'])
        except KeyError:
            self.srs = None

    @property
    def bitdepth(self):
        return self.data['VRTDataset']['VRTRasterBand'][0]['@dataType']

    @property
    def gt(self):
        return [float(x) for x in self.data['VRTDataset']['GeoTransform']['$'].split(',')]

    @property
    def xres(self):
        return self.gt[1]

    @property
    def yres(self):
        return abs(self.gt[5])

    @property
    def tlx(self):
        return self.gt[0]

    @property
    def tly(self):
        return self.gt[3]

    @property
    def shape(self):
        return (self.data['VRTDataset']['@rasterXSize'], self.data['VRTDataset']['@rasterYSize'],
                len(self.data['VRTDataset']['VRTRasterBand']))

    @property
    def bandshape(self):
        return (self.data['VRTDataset']['VRTRasterBand'][0][self.source]['DstRect']['@xSize'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['DstRect']['@ySize'])

    @property
    def epsg(self):
        return self.srs.epsg

    @property
    def filename(self):
        return self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SourceFilename']['$']

    @property
    def blocksize(self):
        try:
            return [self.data['VRTDataset']['BlockXSize']['$'], self.data['VRTDataset']['BlockXSize']['$']]
        except KeyError:
            return [self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SourceProperties']['@BlockXSize'], self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SourceProperties']['@BlockYSize']]

    @property
    def nodata(self):
        try:
            return self.data['VRTDataset']['VRTRasterBand'][0]['NoDataValue']['$']
        except:
            return None

    @nodata.setter
    def nodata(self, value):
        for i in range(self.shape[2]):
           self.data['VRTDataset']['VRTRasterBand'][i]['NoDataValue']['$'] = value

    @property
    def source(self):
        return [x for x in list(self.data['VRTDataset']['VRTRasterBand'][0]) if 'Source' in x][0]

    @property
    def extent(self):
        shape = self.shape
        ymin = self.tly - (shape[1]*self.yres)
        xmax = self.tlx + (shape[0]*self.xres)
        return [self.tlx, xmax, ymin, self.tly]

    def update_src_rect(self, offset):
        for band in range(self.shape[2]):
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@xOff'] = offset[0]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@yOff'] = offset[1]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@xSize'] = offset[2]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@ySize'] = offset[3]

    def update_dst_rect(self, offset):
        for band in range(self.shape[2]):
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@xOff'] = offset[0]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@yOff'] = offset[1]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@xSize'] = offset[2]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@ySize'] = offset[3]

    def pprint(self):
        print(json.dumps(self.data, indent=1))

    def to_xml(self):
        vrtxml = ET.tostring(bf.etree(self.data)[0])
        xml = md.parseString(vrtxml)
        print(xml.toprettyxml())

    def to_gdal(self):
        vrtxml = ET.tostring(bf.etree(self.data)[0])
        ds = gdal.Open(vrtxml)
        return ds

    def to_file(self, outfile, profile=None):
        if profile:
            p = profile(self)
            pname = type(p).__name__.upper()

            if 'COG' in pname:
                _outfile = '/vsimem/testing.tif'
            else:
                _outfile = outfile
            out_ds = gdal.Translate(_outfile, self.to_gdal(), creationOptions=p.creation_options())

            if hasattr(p, "overview_options"):
                for k,v in p.overview_options().items():
                    gdal.SetConfigOption(k, v)
            out_ds.BuildOverviews(p.ovr_resample, p.overviews())

            if 'COG' in pname:
                gdal.Translate(outfile, out_ds, creationOptions=p.creation_options()+['COPY_SRC_OVERVIEWS=YES'])
            out_ds = None
        else:
            gdal.Translate(outfile, self.to_gdal())