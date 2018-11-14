from osgeo import gdal
import xml.etree.ElementTree as ET
from xmljson import badgerfish as bf

def to_file(vrt, outfile, profile=None):
    ds = to_gdal(vrt)
    if profile:
        p = profile(self)
        pname = type(p).__name__.upper()

        if 'COG' in pname:
            _outfile = '/vsimem/testing.tif'
        else:
            _outfile = outfile
        out_ds = gdal.Translate(_outfile, ds, creationOptions=p.creation_options())

        if hasattr(p, "overview_options"):
            for k,v in p.overview_options().items():
                gdal.SetConfigOption(k,v)
            out_ds.BuildOverviews(p.ovr_resample, p.overviews())

        if 'COG' in pname:
            gdal.Translate(outfile, out_ds, creationOptions=p.creation_options()+['COPY_SRC_OVERVIEWS=YES'])
        out_ds = None
    else:
        gdal.Translate(outfile, ds)

def to_gdal(vrt):
    vrtxml = ET.tostring(bf.etree(vrt.data)[0])
    ds = gdal.Open(vrtxml)
    return ds