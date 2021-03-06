import json
from collections import OrderedDict
from typing import Generator, Union
from xmljsonfork import badgerfish as bf
import xml.etree.ElementTree as ET
import copy
import math
import functools
import geojson
from pyproj import Proj, transform
from shapely.ops import transform as transform_geom
from shapely.geometry import shape

from gdaljson.projection import wkt
from gdaljson.transformations import loads, dumps

maxval = {
    "Byte": 2**8,
    "UInt16": 2**16,
    "Int16": int((2**16) / 2),
    "UInt32": 2**32,
    "Int32": int(2**32 / 2),
}


class GeoTransform(object):
    """
    Stores the working copy of the geotransform (GT).  Some of the calculations for warp/translate require retrieving information
    from both the old GT and the new GT (working copy).  This object lets us dynamically update the
    working copy of the GT while preserving the original.  Provides convenience methods for dumping/loading and
    generating inverse GTs.
    """

    @staticmethod
    def inverse_geotransform(gt):
        """Method to calculate the inverse geotransform"""
        inverse = [-(gt[0] / gt[1]), 1 / gt[1], 0, gt[3] / gt[1], 0, 1 / gt[5]]
        return inverse

    @staticmethod
    def from_element(gt_element):
        """Load GT from VRT element"""
        return [float(x) for x in gt_element.split(",")]

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

    def load(self, gt):
        self.tlx = gt[0]
        self.xres = gt[1]
        self.tly = gt[3]
        self.yres = gt[5]

    def to_element(self, inverse=False):
        """Dump the GT or inverse GT to VRT element"""
        if inverse:
            return ",".join(
                [str(x) for x in self.inverse_geotransform(self.gt)])
        return ",".join([str(x) for x in self.gt])


class VRTBase(object):
    """Base clase for VRT parsing.  Contains methods compatible with both VRTDatasets and VRTWarpedDatasets"""

    def __init__(self, vrt):
        if type(vrt) is dict:
            self.data = vrt
        else:
            self.data = loads(vrt)

        self.__gt = GeoTransform(self.data["VRTDataset"]["GeoTransform"]["$"])

    def __str__(self):
        return dumps(self.data).decode('utf-8')

    @property
    def geogname(self):
        return f'tlx_{self.tlx}__tly_{self.tly}__xres_{self.xres}__yres_{self.yres}__cols_{self.xsize}__rows_{self.ysize}'

    @property
    def srs(self):
        try:
            return self.data["VRTDataset"]["SRS"]["$"]
        except KeyError:
            print("WARNING: VRT has no coordinate system")
            return None

    @srs.setter
    def srs(self, wkt_string: str) -> None:
        self.data["VRTDataset"]["SRS"]["$"] = wkt_string

    @property
    def epsg(self):
        if self.srs:
            return self.srs.split(",")[-1][1:-3]
        else:
            return None

    @property
    def is_geographic(self):
        if self.srs.startswith('GEOG'):
            return True
        return False

    @property
    def gt(self):
        return self.__gt

    def update_gt(self):
        self.data["VRTDataset"]["GeoTransform"]["$"] = self.gt.to_element()

    @property
    def tlx(self):
        return self.gt.tlx

    @tlx.setter
    def tlx(self, value: Union[int, float]) -> None:
        self.gt.tlx = value

    @property
    def tly(self):
        return self.gt.tly

    @tly.setter
    def tly(self, value: Union[int, float]) -> None:
        self.gt.tly = value

    @property
    def xres(self):
        return self.gt.xres

    @xres.setter
    def xres(self, value: Union[int, float]) -> None:
        self.gt.xres = value

    @property
    def yres(self):
        return self.gt.yres

    @yres.setter
    def yres(self, value: Union[int, float]) -> None:
        self.gt.yres = value

    @property
    def xsize(self):
        return self.data["VRTDataset"]["@rasterXSize"]

    @xsize.setter
    def xsize(self, value: Union[int, float]) -> None:
        self.data["VRTDataset"]["@rasterXSize"] = value

    @property
    def ysize(self):
        return self.data["VRTDataset"]["@rasterYSize"]

    @ysize.setter
    def ysize(self, value: Union[int, float]) -> None:
        self.data["VRTDataset"]["@rasterYSize"] = value

    @property
    def bands(self):
        return len(self.data["VRTDataset"]["VRTRasterBand"])

    @property
    def shape(self):
        return (self.xsize, self.ysize, self.bands)

    @property
    def bitdepth(self):
        return self.data["VRTDataset"]["VRTRasterBand"][0]["@dataType"]

    @bitdepth.setter
    def bitdepth(self, value: str) -> None:
        [
            self.data["VRTDataset"]["VRTRasterBand"][i]["@dataType"].update({
                "$":
                value
            }) for i in range(self.bands)
        ]

    @property
    def nodata(self):
        try:
            return self.data["VRTDataset"]["VRTRasterBand"][0]["NoDataValue"][
                "$"]
        except:
            return None

    @nodata.setter
    def nodata(self, value: Union[int, float]) -> None:
        [
            self.data["VRTDataset"]["VRTRasterBand"][i]["NoDataValue"].update({
                "$":
                value
            }) for i in range(self.bands)
        ]

    @property
    def extent(self):
        return [
            self.tlx,
            self.tlx + (self.xsize * self.xres),
            self.tly - (self.ysize * self.yres),
            self.tly,
        ]

    @property
    def bandorder(self):
        return [
            self.data["VRTDataset"]["VRTRasterBand"][i]["@band"]
            for i in range(self.bands)
        ]

    def drop_band(self, band: int) -> None:
        self.data["VRTDataset"]["VRTRasterBand"].pop(band - 1)
        # Update all band numbers
        [
            self.data["VRTDataset"]["VRTRasterBand"][i].update({
                "@band": i + 1
            }) for i in range(band - 1, self.bands)
        ]

    def drop_bands(self, bands):
        [
            self.data["VRTDataset"]["VRTRasterBand"].pop(i - 1)
            for i in sorted(bands, reverse=True)
        ]
        [
            self.data["VRTDataset"]["VRTRasterBand"][i].update({
                "@band": i + 1
            }) for i in range(self.bands)
        ]

    def get_band(self, band: int) -> OrderedDict:
        return self.data["VRTDataset"]["VRTRasterBand"][band - 1]

    def get_bands(self, bands: list) -> Generator:
        def gen_band():
            for band in bands:
                yield self.data["VRTDataset"]["VRTRasterBand"][band - 1]

        return gen_band()

    def pprint(self):
        print(json.dumps(self.data, indent=1))

    def to_xml(self, outfile: str) -> None:
        test = bf.etree(self.data)[0]
        tree = ET.ElementTree(test)
        tree.write(outfile)


class VRTDataset(VRTBase):
    """Standard VRT Dataset made with gdal.Translate"""

    def __init__(self, vrt):
        VRTBase.__init__(self, vrt)
        self.source = [
            x for x in list(self.data["VRTDataset"]["VRTRasterBand"][0])
            if "Source" in x
        ][0]

    @property
    def filename(self):
        return self.data["VRTDataset"]["VRTRasterBand"][0][
            self.source]["SourceFilename"]["$"]

    @filename.setter
    def filename(self, value: str) -> None:
        [
            self.data["VRTDataset"]["VRTRasterBand"][i][self.source]
            ["SourceFilename"].update({
                "$": value
            }) for i in range(self.bands)
        ]

    @property
    def scale_ratio(self):
        try:
            return self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["ScaleRatio"]["$"]
        except KeyError:
            return None

    @scale_ratio.setter
    def scale_ratio(self, value: list) -> None:
        [
            self.data["VRTDataset"]["VRTRasterBand"][i][self.source].update({
                "ScaleRatio": {
                    "$": value
                }
            }) for i in range(self.bands)
        ]

    @property
    def scale_offset(self):
        try:
            return self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["ScaleOffset"]["$"]
        except KeyError:
            return None

    @scale_offset.setter
    def scale_offset(self, value: int) -> None:
        [
            self.data["VRTDataset"]["VRTRasterBand"][i][self.source].update({
                "ScaleOffset": {
                    "$": value
                }
            }) for i in range(self.bands)
        ]

    @property
    def resampling(self):
        try:
            return self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["@resampling"]
        except KeyError:
            return "NearestNeighbour"

    @resampling.setter
    def resampling(self, value: str) -> None:
        [
            self.data["VRTDataset"]["VRTRasterBand"][i][self.source].update({
                "@resampling":
                value
            }) for i in range(self.bands)
        ]

    @property
    def blocksize(self):
        return [
            self.data["VRTDataset"]["VRTRasterBand"][0]["SimpleSource"]["SourceProperties"]["@BlockXSize"],
            self.data["VRTDataset"]["VRTRasterBand"][0]["SimpleSource"]["SourceProperties"]["@BlockYSize"]
        ]

    @property
    def src_rect(self):
        return [
            self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["SrcRect"]["@xOff"],
            self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["SrcRect"]["@yOff"],
            self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["SrcRect"]["@xSize"],
            self.data["VRTDataset"]["VRTRasterBand"][0][self.source]["SrcRect"]
            ["@ySize"],
        ]

    @src_rect.setter
    def src_rect(self, offset: list) -> None:
        for band in range(self.shape[2]):
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["SrcRect"]["@xOff"] = offset[0]
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["SrcRect"]["@yOff"] = offset[1]
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["SrcRect"]["@xSize"] = offset[2]
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["SrcRect"]["@ySize"] = offset[3]

    @property
    def dst_rect(self):
        return [
            self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["DstRect"]["@xOff"],
            self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["DstRect"]["@yOff"],
            self.data["VRTDataset"]["VRTRasterBand"][0][
                self.source]["DstRect"]["@xSize"],
            self.data["VRTDataset"]["VRTRasterBand"][0][self.source]["DstRect"]
            ["@ySize"],
        ]

    @dst_rect.setter
    def dst_rect(self, offset: list) -> None:
        for band in range(self.shape[2]):
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["DstRect"]["@xOff"] = offset[0]
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["DstRect"]["@yOff"] = offset[1]
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["DstRect"]["@xSize"] = offset[2]
            self.data["VRTDataset"]["VRTRasterBand"][band][
                self.source]["DstRect"]["@ySize"] = offset[3]

    def change_source(self, new_source: str) -> None:
        for band in range(self.bands):
            self.data["VRTDataset"]["VRTRasterBand"][band].update({
                new_source:
                self.data["VRTDataset"]["VRTRasterBand"][band][self.source]
            })
            del (self.data["VRTDataset"]["VRTRasterBand"][band][self.source])

            if new_source == "ComplexSource":
                self.data["VRTDataset"]["VRTRasterBand"][band][
                    new_source].update({
                        "NODATA": {
                            "$": self.nodata
                        }
                    })
                self.data["VRTDataset"]["VRTRasterBand"][band][new_source][
                    "SourceProperties"]["@BlockXSize"] = min(128, self.xsize)
                self.data["VRTDataset"]["VRTRasterBand"][band][new_source][
                    "SourceProperties"]["@BlockYSize"] = min(128, self.ysize)
        self.source = new_source

    def add_band(self):
        """Add one band with same band profile as Band1 and ambiguous color interp"""
        template_band = copy.deepcopy(self.get_band(1))
        template_band["@band"] = self.bands + 1
        if "ColorInterp" in template_band.keys():
            del (template_band["ColorInterp"])
        self.data["VRTDataset"]["VRTRasterBand"].append(template_band)

    def add_bands(self, bands: int) -> None:
        """Generate band(s) with same band profile as Band1 and ambiguous color interp"""
        # [self.add_band() for _ in range(bands)]
        for _ in range(bands):
            self.add_band()

    def translate(
            self,
            bandList: list = None,
            srcWin: list = None,
            projWin: list = None,
            height: int = None,
            width: int = None,
            xRes: Union[int, float] = None,
            yRes: Union[int, float] = None,
            noData: Union[int, float] = None,
            resampleAlg: str = None,
            scaleParams: list = None,
            **kwargs
    ) -> None:

        # Handle bands first
        if bandList:
            self.drop_bands(
                set(range(1, self.bands + 1)).difference(set(bandList)))
            [
                self.data["VRTDataset"]["VRTRasterBand"][i][self.source]
                ["SourceBand"].update({
                    "$": bandList[i]
                }) for i in range(self.bands)
            ]
        if srcWin or projWin:
            if srcWin and projWin:
                raise ValueError("srcWin and projWin are mutually exlusive")
            if projWin:
                xoff, yoff = [
                    int((projWin[0] - self.gt.tlx) / self.gt.xres),
                    int((self.gt.tly - projWin[1]) / self.gt.yres),
                ]
                xsize, ysize = [
                    int(round((projWin[2] - projWin[0]) / self.gt.xres)),
                    int(round((projWin[1] - projWin[3]) / self.gt.yres)),
                ]
                srcWin = [xoff, yoff, xsize, ysize]
            self.src_rect = srcWin
            self.dst_rect = [0, 0, srcWin[2], srcWin[3]]

        self.tlx = self.src_rect[0] * self.xres + self.tlx
        self.tly = self.tly - self.src_rect[1] * self.yres

        if height or width:
            if (height or width) and (xRes or yRes):
                raise ValueError(
                    "height/width and xRes/yRes are mutually exclusive")
            if height and width:
                self.dst_rect = [0, 0, width, height]
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
                self.dst_rect = [0, 0, _width, _height]

            self.xres = self.xres * self.src_rect[2] / _width
            self.yres = -(self.yres * self.src_rect[3]) / _height

        elif xRes and yRes:
            _width = int(round((self.xres * self.src_rect[2]) / xRes))
            _height = int(round((self.yres * self.src_rect[3]) / yRes))
            self.xres = xRes
            self.yres = -yRes
            self.dst_rect = [0, 0, _width, _height]

        self.update_gt()
        self.xsize = self.dst_rect[2]
        self.ysize = self.dst_rect[3]

        if scaleParams:
            self.scale_ratio = scaleParams[3] / scaleParams[1]
            self.scale_offset = 0
            self.change_source("ComplexSource")

        if noData:
            self.nodata = noData
        if resampleAlg:
            self.resampling = resampleAlg


class VRTWarpedDataset(VRTBase):
    """
    VRTDataset with subClass="VRTWarpedDataset" containing a GDALWarpOptions element which describes a warping operation.
    VRTWarpedDataset has a different spec than VRTDataset.  This class expects the contained VRT to be in VRTWarpedDataset
    format (tests/templates/warped.vrt).
    """

    def __init__(self, vrt):
        super().__init__(vrt)

        self.__warp_options = WarpOpts(
            self.data["VRTDataset"]["GDALWarpOptions"])

    @property
    def filename(self):
        return self.data["VRTDataset"]["GDALWarpOptions"]["SourceDataset"]["$"]

    @filename.setter
    def filename(self, value: str) -> None:
        self.data["VRTDataset"]["GDALWarpOptions"]["SourceDataset"][
            "$"] = value

    @property
    def blocksize(self):
        return [
            self.data["VRTDataset"]["BlockXSize"]["$"],
            self.data["VRTDataset"]["BlockXSize"]["$"],
        ]

    @blocksize.setter
    def blocksize(self, value: list) -> None:
        self.data["VRTDataset"]["BlockXSize"]["$"] = value[0]
        self.data["VRTDataset"]["BlockYSize"]["$"] = value[1]

    @property
    def warp_options(self):
        return self.__warp_options

    @warp_options.setter
    def warp_options(self, value: dict) -> None:
        self.data["VRTDataset"]["GDALWarpOptions"].update(value)

    def add_band(self, alpha: bool = False) -> None:
        """Add one band with same band profile as Band1 and ambiguous color interp"""
        bands = self.bands
        template_band = copy.deepcopy(self.get_band(1))
        template_band["@band"] = bands + 1
        if alpha:
            template_band["ColorInterp"].update({"$": "Alpha"})
        else:
            if "ColorInterp" in template_band.keys():
                del (template_band["ColorInterp"])
        self.data["VRTDataset"]["VRTRasterBand"].append(template_band)

        # Also update band mapping
        if not alpha:
            template_mapping = copy.deepcopy(
                self.data["VRTDataset"]["GDALWarpOptions"]["BandList"]
                ["BandMapping"][0])
            template_mapping["@src"] = template_mapping["@dst"] = bands + 1
            self.data["VRTDataset"]["GDALWarpOptions"]["BandList"][
                "BandMapping"].append(template_mapping)

    def add_bands(self, bands: int) -> None:
        """Generate band(s) with same band profile as Band1 and ambiguous color interp"""
        [self.add_band() for _ in range(bands)]

    def filter_band_properties(self, allowed: list) -> None:
        """Delete all band elements not in the input list"""
        for band in self.data["VRTDataset"]["VRTRasterBand"]:
            for (k, v) in dict(band).items():
                if k not in allowed:
                    del (band[k])

    def warp(
            self,
            dstSRS: int = None,
            clipper: Union[str, dict] = None,
            cropToCutline: bool = False,
            height: int = None,
            width: int = None,
            xRes: Union[int, float] = None,
            yRes: Union[int, float] = None,
            dstAlpha: bool = False,
            resample: str = "NearestNeighbour",
            **kwargs
    ) -> None:

        self.warp_options.resample = resample

        if dstSRS:
            extent = self.extent
            out_wkt = wkt(dstSRS)
            in_srs = Proj(init=f"epsg:{self.epsg}")
            out_srs = Proj(init=f"epsg:{dstSRS}")

            # Calculate new resolution (see https://www.gdal.org/gdal__alg_8h.html#a816819e7495bfce06dbd110f7c57af65)
            # Resolution is computed with the intent that the length of the distance from the top left corner of the output
            # imagery to the bottom right corner would represent the same number of pixels as in the source

            source_pixels_diag = math.sqrt(self.xsize**2 + self.ysize**2)
            proj_tl = transform(in_srs, out_srs, extent[0], extent[3])
            proj_bl = transform(in_srs, out_srs, extent[0], extent[2])
            proj_br = transform(in_srs, out_srs, extent[1], extent[2])
            proj_tr = transform(in_srs, out_srs, extent[1], extent[3])

            proj_tl_corner = [
                min(proj_tl[0], proj_bl[0]),
                max(proj_tl[1], proj_tr[1])
            ]
            proj_br_corner = [
                max(proj_tr[0], proj_br[0]),
                min(proj_bl[1], proj_br[1])
            ]

            projwidth = proj_br[0] - proj_tl[0]
            projheight = proj_tl[1] - proj_br[1]
            projdiag = math.sqrt(projwidth**2 + projheight**2)
            res = projdiag / source_pixels_diag

            # Calculate new cols and rows based on res
            cols = round((proj_br_corner[0] - proj_tl_corner[0]) / res)
            rows = round((proj_tl_corner[1] - proj_br_corner[1]) / res)

            proj_gt = [proj_tl_corner[0], res, 0, proj_tl_corner[1], 0, -res]
            self.gt.load(proj_gt)

            # Update transformer
            self.warp_options.reproject_transformer = {
                "ReprojectionTransformer": {
                    "SourceSRS": {
                        "$": self.srs
                    },
                    "TargetSRS": {
                        "$": out_wkt
                    },
                }
            }
            self.warp_options.dst_gt = self.gt.to_element()
            self.warp_options.dst_invgt = self.gt.to_element(inverse=True)
            self.srs = out_wkt
            self.xsize = cols
            self.ysize = rows

        if clipper:
            if hasattr(clipper, "__geo_interface__"):
                geom = shape(clipper)
            elif type(clipper) is str and clipper.endswith(".geojson"):
                clip_file = open(clipper)
                geom = shape(geojson.load(clip_file)["geometry"])
            elif type(clipper) is dict:
                geom = shape(geojson.loads(json.dumps(clipper)))
            else:
                raise ValueError("Invalid clipper type")

            self.warp_options.cutline = transform_geom(self.coords_to_pix,
                                                       geom).wkt

            if cropToCutline:
                if dstSRS:
                    project = functools.partial(transform, in_srs, out_srs)
                    geom = transform_geom(project, geom)
                bounds = geom.bounds
                xsize, ysize = [
                    int(round((bounds[2] - bounds[0]) / self.xres)),
                    int(round((bounds[3] - bounds[1]) / self.yres)),
                ]
                clip_gt = [
                    bounds[0],
                    (bounds[2] - bounds[0]) / xsize,
                    0,
                    bounds[3],
                    0,
                    -((bounds[3] - bounds[1]) / ysize),
                ]
                self.xsize = xsize
                self.ysize = ysize

                self.gt.load(clip_gt)
            self.warp_options.dst_gt = self.gt.to_element()
            self.warp_options.dst_invgt = self.gt.to_element(inverse=True)

        if type(clipper) is str and clipper.endswith(".geojson"):
            clip_file.close()

        if height or width:
            if (height or width) and (xRes or yRes):
                raise ValueError(
                    "height/width and xRes/yRes are mutually exclusive")
            if height and width:
                _height = height
                _width = width
                _xres = (self.xres * self.xsize) / _width
                _yres = (self.yres * self.ysize) / _height
            else:
                if width:
                    _xres = (self.xres * self.xsize) / width
                    _yres = -_xres
                    _height = int(
                        round((self.extent[2] - self.extent[3]) / _yres))
                    _width = width
                elif height:
                    _yres = (self.yres * self.ysize) / height
                    _xres = abs(_yres)
                    _width = int(
                        round((self.extent[1] - self.extent[0]) / _xres))
                    _height = height
            self.xres = _xres
            self.yres = _yres
            self.xsize = _width
            self.ysize = _height

        elif xRes and yRes:
            _width = int(round((self.xres * self.xsize) / xRes))
            _height = int(round((self.yres * self.ysize) / yRes))

            self.xres = xRes
            self.yres = -yRes
            self.xsize = _width
            self.ysize = _height

        if dstAlpha:
            self.add_band(alpha=True)
            self.warp_options.alphaband = self.bands
            self.warp_options.add_option({
                "@name": "DST_ALPHA_MAX",
                "$": maxval[self.bitdepth] - 1
            })
            self.warp_options.opts["Option"][0]["$"] = 0
            self.warp_options.reset_nodata()
            self.filter_band_properties([
                "ColorInterp", "@dataType", "@band", "@subClass",
                "VRTRasterBand"
            ])

        if min(self.blocksize) > max(self.xsize, self.ysize):
            self.blocksize = [self.xsize, self.xsize]

        self.update_gt()
        self.warp_options = self.warp_options.dumps()

    def coords_to_pix(self, x: float, y: float, z: float = None) -> tuple:
        """"""
        gt = GeoTransform(self.data["VRTDataset"]["GeoTransform"]["$"])
        return ((x - gt.tlx) / gt.xres, (gt.tly - y) / gt.yres)


class WarpOpts:
    """Class for manipulating gdal.Warp options"""

    def __init__(self, gdalwarp_opts):
        self.opts = gdalwarp_opts
        self.opts["Option"] = [self.opts["Option"]]

    @property
    def warp_memory_limit(self):
        return self.opts["WarpMemoryLimit"]["$"]

    @warp_memory_limit.setter
    def warp_memory_limit(self, value: Union[int, float]) -> None:
        self.opts["WarpMemoryLimit"]["$"] = value

    @property
    def resample(self):
        return self.opts["ResampleAlg"]["$"]

    @resample.setter
    def resample(self, value: str) -> None:
        self.opts["ResampleAlg"]["$"] = value

    @property
    def reproject_transformer(self):
        try:
            return self.proj_transformer["ReprojectTransformer"]
        except ValueError:
            return None

    @reproject_transformer.setter
    def reproject_transformer(self, d: dict) -> None:
        self.opts["Transformer"]["ApproxTransformer"]["BaseTransformer"][
            "GenImgProjTransformer"].update({
                "ReprojectTransformer": d
            })

    @property
    def proj_transformer(self):
        return self.opts["Transformer"]["ApproxTransformer"][
            "BaseTransformer"]["GenImgProjTransformer"]

    @property
    def src_gt(self):
        return self.proj_transformer["SrcGeoTransform"]["$"]

    @property
    def dst_gt(self):
        return self.proj_transformer["DstGeoTransform"]["$"]

    @dst_gt.setter
    def dst_gt(self, value: str) -> None:
        self.opts["Transformer"]["ApproxTransformer"]["BaseTransformer"][
            "GenImgProjTransformer"]["DstGeoTransform"]["$"] = value

    @property
    def dst_invgt(self):
        return self.proj_transformer["DstInvGeoTransform"]["$"]

    @dst_invgt.setter
    def dst_invgt(self, value: str) -> None:
        self.opts["Transformer"]["ApproxTransformer"]["BaseTransformer"][
            "GenImgProjTransformer"]["DstInvGeoTransform"]["$"] = value

    @property
    def cutline(self):
        return self.opts["Cutline"]["$"]

    @cutline.setter
    def cutline(self, value: str) -> None:
        self.opts.update({"Cutline": {"$": value}})

    @property
    def alphaband(self):
        return self.opts["DstAlphaBand"]["$"]

    @alphaband.setter
    def alphaband(self, value: int) -> None:
        self.opts.update({"DstAlphaBand": {"$": value}})

    def add_option(self, option: dict) -> None:
        self.opts["Option"].append(option)

    def reset_nodata(self):
        for band in self.opts["BandList"]["BandMapping"]:
            del (band["DstNoDataReal"])
            del (band["DstNoDataImag"])

    def dumps(self):
        return self.opts
