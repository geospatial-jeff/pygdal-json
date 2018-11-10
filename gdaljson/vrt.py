import json
from xmljson import badgerfish as bf
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
import copy

from gdaljson.projection import SpatialRef
from gdaljson.transformations import loads

from osgeo import gdal

class VRTBase(object):

    def __init__(self, vrt):
        if type(vrt) is dict:
            self.data = vrt
        else:
            self.data = loads(vrt)
        try:
            self.srs = SpatialRef(self.data['VRTDataset']['SRS']['$'])
        except KeyError:
            self.srs = None

        self.__gt = GeoTransform(self.data['VRTDataset']['GeoTransform']['$'])

    @property
    def gt(self):
        return self.__gt

    def update_gt(self):
        self.data['VRTDataset']['GeoTransform']['$'] = self.gt.to_element()

    @property
    def tlx(self):
        return self.gt.tlx

    @tlx.setter
    def tlx(self, value):
        self.gt.tlx = value

    @property
    def tly(self):
        return self.gt.tly

    @tly.setter
    def tly(self, value):
        self.gt.tly = value

    @property
    def xres(self):
        return self.gt.xres

    @xres.setter
    def xres(self, value):
        self.gt.xres = value

    @property
    def yres(self):
        return self.gt.yres

    @yres.setter
    def yres(self, value):
        self.gt.yres = value

    @property
    def xsize(self):
        return self.data['VRTDataset']['@rasterXSize']

    @xsize.setter
    def xsize(self, value):
        self.data['VRTDataset']['@rasterXSize'] = value

    @property
    def ysize(self):
        return self.data['VRTDataset']['@rasterYSize']

    @ysize.setter
    def ysize(self, value):
        self.data['VRTDataset']['@rasterYSize'] = value

    @property
    def bands(self):
        return len(self.data['VRTDataset']['VRTRasterBand'])

    @property
    def shape(self):
        return [self.xsize, self.ysize, self.bands]

    @property
    def bitdepth(self):
        return self.data['VRTDataset']['VRTRasterBand'][0]['@dataType']

    @bitdepth.setter
    def bitdepth(self, value):
        [self.data['VRTDataset']['VRTRasterBand'][i]['@dataType'].update({'$': value}) for i in range(self.bands)]

    @property
    def nodata(self):
        try:
            return self.data['VRTDataset']['VRTRasterBand'][0]['NoDataValue']['$']
        except:
            return None

    @nodata.setter
    def nodata(self, value):
        [self.data['VRTDataset']['VRTRasterBand'][i]['NoDataValue'].update({'$': value}) for i in range(self.bands)]

    def drop_band(self, band):
        self.data['VRTDataset']['VRTRasterBand'].pop(band - 1)

    def drop_bands(self, bands):
        [self.data['VRTDataset']['VRTRasterBand'].pop(i - 1) for i in sorted(bands, reverse=True)]

    def get_band(self, band):
        return self.data['VRTDataset']['VRTRasterBand'][band - 1]

    def get_bands(self, bands):
        def gen_band():
            for band in bands:
                yield self.data['VRTDataset']['VRTRasterBand'][band - 1]
        return gen_band()

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

class VRTDataset(VRTBase):

    """Standard VRT Dataset made with gdal.Translate"""

    def __init__(self, vrt):
        VRTBase.__init__(self, vrt)
        self.source = [x for x in list(self.data['VRTDataset']['VRTRasterBand'][0]) if 'Source' in x][0]

    @property
    def scale_ratio(self):
        try:
            return self.data['VRTDataset']['VRTRasterBand'][0][self.source]['ScaleRatio']['$']
        except KeyError:
            return None

    @scale_ratio.setter
    def scale_ratio(self, value):
        [self.data['VRTDataset']['VRTRasterBand'][i][self.source].update({'ScaleRatio': {'$': value}}) for i in range(self.bands)]

    @property
    def scale_offset(self):
        try:
            return self.data['VRTDataset']['VRTRasterBand'][0][self.source]['ScaleOffset']['$']
        except KeyError:
            return None

    @scale_offset.setter
    def scale_offset(self, value):
        [self.data['VRTDataset']['VRTRasterBand'][i][self.source].update({'ScaleOffset': {'$': value}}) for i in range(self.bands)]

    @property
    def resampling(self):
        try:
            return self.data['VRTDataset']['VRTRasterBand'][0][self.source]['@resampling']
        except KeyError:
            return "NearestNeighbour"

    @resampling.setter
    def resampling(self, value):
        [self.data['VRTDataset']['VRTRasterBand'][i][self.source].update({'@resampling': value}) for i in range(self.bands)]

    @property
    def src_rect(self):
        return [self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SrcRect']['@xOff'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SrcRect']['@yOff'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SrcRect']['@xSize'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['SrcRect']['@ySize']
        ]

    @src_rect.setter
    def src_rect(self, offset):
        for band in range(self.shape[2]):
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@xOff'] = offset[0]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@yOff'] = offset[1]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@xSize'] = offset[2]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['SrcRect']['@ySize'] = offset[3]

    @property
    def dst_rect(self):
        return [self.data['VRTDataset']['VRTRasterBand'][0][self.source]['DstRect']['@xOff'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['DstRect']['@yOff'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['DstRect']['@xSize'],
                self.data['VRTDataset']['VRTRasterBand'][0][self.source]['DstRect']['@ySize']
        ]

    @dst_rect.setter
    def dst_rect(self, offset):
        for band in range(self.shape[2]):
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@xOff'] = offset[0]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@yOff'] = offset[1]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@xSize'] = offset[2]
            self.data['VRTDataset']['VRTRasterBand'][band][self.source]['DstRect']['@ySize'] = offset[3]

    def change_source(self, new_source):
        for band in range(self.bands):
            self.data['VRTDataset']['VRTRasterBand'][band].update({new_source: self.data['VRTDataset']['VRTRasterBand'][band][self.source]})
            del(self.data['VRTDataset']['VRTRasterBand'][band][self.source])

            if new_source == "ComplexSource":
                self.data['VRTDataset']['VRTRasterBand'][band][new_source].update({"NODATA": {"$": self.nodata}})
                self.data['VRTDataset']['VRTRasterBand'][band][new_source]['SourceProperties']['@BlockXSize'] = min(128,self.xsize)
                self.data['VRTDataset']['VRTRasterBand'][band][new_source]['SourceProperties']['@BlockYSize'] = min(128,self.ysize)



        self.source = new_source

    def add_band(self):
        template_band = copy.deepcopy(self.get_band(1))
        template_band['@band'] = self.bands+1
        if 'ColorInterp' in template_band.keys():
            del(template_band['ColorInterp'])
        self.data['VRTDataset']['VRTRasterBand'].append(template_band)

    def add_bands(self, bands):
        """Generate band(s) with same band profile as Band1 and ambiguous color interp"""
        [self.add_band() for _ in range(bands)]

    def translate(self, bandList=None, srcWin=None, projWin=None, height=None, width=None, xRes=None, yRes=None,
                    nodata=None, resampleAlg=None, scaleParams=None):
        """https://github.com/gina-alaska/dans-gdal-scripts"""
        originalvrt = copy.deepcopy(self)

        #Handle bands first
        if bandList:
            self.drop_bands(set(range(1,self.bands+1)).difference(set(bandList)))
            [self.data['VRTDataset']['VRTRasterBand'][i][self.source]['SourceBand'].update({'$': bandList[i]}) for i in range(self.bands)]
        if srcWin or projWin:
            if srcWin and projWin:
                raise ValueError("srcWin and projWin are mutually exlusive")
            if projWin:
                xoff, yoff = [int((projWin[0] - self.gt.tlx) / self.gt.xres),
                              int((self.gt.tly - projWin[1]) / self.gt.yres)]
                xsize, ysize = [int((projWin[2] - projWin[0]) / self.gt.xres),
                                int((projWin[1] - projWin[3]) / self.gt.yres)]
                srcWin = [xoff, yoff, xsize, ysize]
            self.src_rect = srcWin
            self.dst_rect = [0, 0, srcWin[2], srcWin[3]]

        self.tlx = self.src_rect[0] * self.xres + self.tlx
        self.tly = self.tly - self.src_rect[1] * self.yres

        if height or width:
            if (height or width) and (xRes or yRes):
                raise ValueError("height/width and xRes/yRes are mutually exclusive")
            if height and width:
                self.dst_rect = [0,0,width,height]
                _width = width
                _height = height
            else:
                if height:
                    ratio = self.src_rect[3] / height
                    _width = int(round(self.src_rect[2] / ratio))
                    _height = height
                elif width:
                    ratio = self.src_rect[2] / width
                    _height = int(round(self.src_rect[3] / ratio))
                    _width = width
                self.dst_rect = [0,0,_width,_height]
            self.xres = self.xres * self.src_rect[2]
            self.yres = -(self.yres * self.src_rect[3])

        elif xRes and yRes:
            _width = int(round((self.xres * self.src_rect[2]) / xRes))
            _height = int(round((self.yres * self.src_rect[3]) / yRes))
            self.xres = xRes
            self.yres = -yRes
            self.dst_rect = [0,0,_width,_height]

        self.update_gt()
        self.xsize = self.dst_rect[2]
        self.ysize = self.dst_rect[3]

        if scaleParams:
            self.scale_ratio = scaleParams[3] / scaleParams[1]
            self.scale_offset = 0
            self.change_source("ComplexSource")

        if nodata:
            self.nodata = nodata
        if resampleAlg:
            self.resampling = resampleAlg

class VRTWarpedDataset(VRTBase):

    """
    VRTDataset with subClass="VRTWarpedDataset" containing a GDALWarpOptions element which describes a warping operation.
    VRTWarpedDataset has a different spec than VRTDataset.  This class expects the contained VRT to be in VRTWarpedDataset
    format (../templates/warped.vrt).
    """
    def __init__(self, vrt):
        super().__init__(vrt)

    def add_band(self):
        bands = self.bands
        template_band = copy.deepcopy(self.get_band(1))
        template_band['@band'] = bands+1
        if 'ColorInterp' in template_band.keys():
            del(template_band['ColorInterp'])
        self.data['VRTDataset']['VRTRasterBand'].append(template_band)

        #Also update band mapping
        template_mapping = copy.deepcopy(self.data['VRTDataset']['GDALWarpOptions']['BandList']['BandMapping'][0])
        template_mapping['@src'] = template_mapping['@dst'] = bands+1
        self.data['VRTDataset']['GDALWarpOptions']['BandList']['BandMapping'].append(template_mapping)

    def add_bands(self, bands):
        """Generate band(s) with same band profile as Band1 and ambiguous color interp"""
        [self.add_band() for _ in range(bands)]

class GeoTransform(object):

    @staticmethod
    def from_element(gt_element):
        return [float(x) for x in gt_element.split(',')]

    def __init__(self, gt_element):
        self.gt = self.from_element(gt_element)

    @property
    def tlx(self):
        return self.gt[0]

    @tlx.setter
    def tlx(self, value):
        self.gt[0] = value

    @property
    def tly(self):
        return self.gt[3]

    @tly.setter
    def tly(self, value):
        self.gt[3] = value

    @property
    def xres(self):
        return self.gt[1]

    @xres.setter
    def xres(self, value):
        self.gt[1] = value

    @property
    def yres(self):
        return abs(self.gt[5])

    @yres.setter
    def yres(self, value):
        self.gt[5] = value

    def to_element(self):
        return ','.join([str(x) for x in self.gt])

# with open('../templates/translate.vrt') as vrtfile:
#     vrt = VRTDataset(vrtfile.read())
#     vrt.translate(scaleParams=[0,13175,0,255])
#     vrt.to_file('test_8bit.tif')
