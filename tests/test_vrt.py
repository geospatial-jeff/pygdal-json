import unittest
from contextlib import contextmanager
import os
import uuid

from osgeo import gdal

from gdaljson import VRTDataset, VRTWarpedDataset
from gdaljson.vrt import GeoTransform

import gdaljson_utils as utils

gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

class VRTTestCases(unittest.TestCase):

    """
    Testing equivalency between VRT made natively with gdal (gdal.Warp/gdal.Translate) and VRT made with gdaljson
    """

    @staticmethod
    def read_vsimem(fn):
        '''Read GDAL vsimem files'''
        vsifile = gdal.VSIFOpenL(fn, 'r')
        gdal.VSIFSeekL(vsifile, 0, 2)
        vsileng = gdal.VSIFTellL(vsifile)
        gdal.VSIFSeekL(vsifile, 0, 0)
        return gdal.VSIFReadL(1, vsileng, vsifile)

    def setUp(self):
        self.warpedvrt = 'templates/warped.vrt'
        self.translatevrt = 'templates/translate.vrt'

    @contextmanager
    def open_vrt(self, fpath):
        vrtfile = open(fpath)
        if 'warped' in fpath:
            vrt = VRTWarpedDataset(vrtfile.read())
        else:
            vrt = VRTDataset(vrtfile.read())
        vrt.filename = os.path.join(os.path.split(__file__)[0], 'templates', vrt.filename)
        yield vrt
        vrtfile.close()

    def translate(self, **kwargs):
        with self.open_vrt(self.translatevrt) as vrt:
            vrt.translate(**kwargs)
            gdaljson_translate = vrt

        if 'scaleParams' in list(kwargs):
            kwargs['scaleParams'] = [kwargs['scaleParams']]

        fname = '/vsimem/{}.vrt'.format(str(uuid.uuid4().hex))
        gdal.Translate(fname, gdal.Open(self.translatevrt), **kwargs)
        xml_string = self.read_vsimem(fname)
        native_translate = VRTDataset(xml_string)
        return [native_translate, gdaljson_translate]

    def warp(self, **kwargs):
        with self.open_vrt(self.warpedvrt) as vrt:
            vrt.warp(**kwargs)
            gdaljson_warp = vrt

        if 'dstSRS' in list(kwargs):
            kwargs['dstSRS'] = 'EPSG:{}'.format(kwargs['dstSRS'])
        if 'clipper' in list(kwargs):
            kwargs['cutlineDSName'] = kwargs['clipper']
            del(kwargs['clipper'])

        fname = '/vsimem/{}.vrt'.format(str(uuid.uuid4().hex))
        gdal.Warp(fname, gdal.Open(self.translatevrt), **kwargs)
        xml_string = self.read_vsimem(fname)
        native_warp = VRTWarpedDataset(xml_string)
        return [native_warp, gdaljson_warp]


    def check_equivalency(self, vrt1, vrt2):
        properties = ['xsize', 'ysize', 'tlx', 'tly', 'xres', 'yres', 'epsg', 'bitdepth', 'nodata', 'extent']
        if type(vrt1) == type(vrt2) == VRTDataset:
            self.assertListEqual(vrt1.src_rect, vrt2.src_rect)
            self.assertListEqual(vrt1.dst_rect, vrt1.dst_rect)
            self.assertEqual(vrt1.source, vrt2.source)
            tolerance = 18
        elif type(vrt1) == type(vrt2) == VRTWarpedDataset:
            self.assertListEqual(vrt1.blocksize, vrt2.blocksize)
            tolerance = 8

        for item in properties:
            try:
                val1 = getattr(vrt1, item)
                val2 = getattr(vrt2, item)
                if type(val1) == list:
                    for (x,y) in zip(val1, val2):
                        self.assertAlmostEqual(x,y,tolerance)
                else:
                    self.assertAlmostEqual(val1, val2, tolerance)
            except AssertionError:
                print("Invalid property: {}".format(item))
                raise

    def test_translate_bands(self):
        #Dropping bands with translate
        native, gdaljson = self.translate(bandList=[1,2,3])
        self.check_equivalency(native, gdaljson)

        #Reordering bands with translate
        native, gdaljson = self.translate(bandList=[4,3,2,1])
        self.check_equivalency(native, gdaljson)
        self.assertListEqual(native.bandorder, gdaljson.bandorder)

        #Dropping bands with VRT interface
        gdaljson.drop_band(1) #Drop the first band
        self.assertEqual(gdaljson.bands, 3)
        self.assertEqual(gdaljson.bandorder, [1,2,3])
        gdaljson.drop_bands([1,2]) #Drop the first and second bands
        self.assertEqual(gdaljson.bands, 1)
        self.assertEqual(gdaljson.bandorder, [1])

    def test_translate_srcwin(self):
        # [xoff, yoff, xsize, ysize] in pixel coords
        offset = [0,0,100,100]
        native, gdaljson = self.translate(srcWin=offset)
        self.check_equivalency(native, gdaljson)

    def test_translate_projwin(self):
        #[xmin, ymax, xmax, ymin] in projected units
        with self.open_vrt(self.translatevrt) as vrt:
            extent = vrt.extent
            offset = [vrt.tlx, vrt.tly, (extent[1] + extent[0]) / 2, (extent[3] + extent[2]) / 2]

        native, gdaljson = self.translate(projWin=offset)
        self.check_equivalency(native, gdaljson)

    def test_translate_width_height(self):
        native, gdaljson = self.translate(height=500)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.translate(width=500)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.translate(width=500, height=480)
        self.check_equivalency(native, gdaljson)

    def test_translate_resample(self):
        with self.open_vrt(self.translatevrt) as vrt:
            native, gdaljson = self.translate(xRes=vrt.xres/2, yRes=vrt.yres/2)
            self.check_equivalency(native, gdaljson)

            native, gdaljson = self.translate(xRes=vrt.xres/2, yRes=vrt.yres/2, resampleAlg='Cubic')
            self.check_equivalency(native, gdaljson)

    def test_scale_params(self):
        native, gdaljson = self.translate(scaleParams=[0,1400,0,255])
        self.check_equivalency(native, gdaljson)

    def test_translate_nodata(self):
        native, gdaljson = self.translate(noData=100)
        self.check_equivalency(native, gdaljson)

    def test_warp_srs(self):
        native, gdaljson = self.warp(dstSRS=3857)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(dstSRS=32611)
        self.check_equivalency(native, gdaljson)

    def test_warp_clipper(self):
        clipper = 'templates/clipper.geojson'

        native, gdaljson = self.warp(clipper=clipper)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(clipper=clipper, cropToCutline=True)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(clipper=clipper, cropToCutline=True, dstAlpha=True)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(clipper=clipper, cropToCutline=True, height=250)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(clipper=clipper, cropToCutline=True, height=250, width=150)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(clipper=clipper, dstSRS=3857)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(clipper=clipper, dstSRS=3857, dstAlpha=True, height=100, width=100)
        self.check_equivalency(native, gdaljson)

    def test_warp_width_height(self):
        native, gdaljson = self.warp(width=500)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(height=500)
        self.check_equivalency(native, gdaljson)

        native, gdaljson = self.warp(width=500, height=480)
        self.check_equivalency(native, gdaljson)

    def test_warp_resample(self):
        with self.open_vrt(self.warpedvrt) as vrt:
            native, gdaljson = self.warp(xRes=vrt.xres/2, yRes=vrt.yres/2)
            self.check_equivalency(native, gdaljson)

            native, gdaljson = self.warp(xRes=30, yRes=30, dstSRS=3857)
            self.check_equivalency(native, gdaljson)