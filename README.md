# pygdal-json

A simple Python module for JSON-encoding the GDAL Data Model.

### GDAL VRT Format
GDAL's VRT driver is a format driver for GDAL that allows a virtual GDAL dataset to be composed from other GDAL datasets with repositioning, and algorithms potentially applied as well as various kinds of metadata altered or added.  VRT descriptions of datasets can be saved in an XML format normally given the extension `.vrt`.  An exapmle of a simple .vrt file referring to a 512x512 dataset with one-band and no projection loaded from utm.tif might look like:

```xml
<VRTDataset rasterXSize="512" rasterYSize="512">
  <GeoTransform>440720.0, 60.0, 0.0, 3751320.0, 0.0, -60.0</GeoTransform>
  <VRTRasterBand dataType="Byte" band="1">
    <ColorInterp>Gray</ColorInterp>
    <SimpleSource>
      <SourceFilename relativeToVRT="1">utm.tif</SourceFilename>
      <SourceBand>1</SourceBand>
      <SrcRect xOff="0" yOff="0" xSize="512" ySize="512"/>
      <DstRect xOff="0" yOff="0" xSize="512" ySize="512"/>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
```

Pygdal-json uses the [xmljson](https://github.com/sanand0/xmljson) module to parse .vrt files into JSON representations:

```json
{
 "VRTDataset": {
  "@rasterXSize": 512,
  "@rasterYSize": 512,
  "GeoTransform": {
   "$": "440720.0, 60.0, 0.0, 3751320.0, 0.0, -60.0"
  },
  "VRTRasterBand": {
   "@dataType": "Byte",
   "@band": 1,
   "ColorInterp": {
    "$": "Gray"
   },
   "SimpleSource": {
    "SourceFilename": {
     "@relativeToVRT": 1,
     "$": "utm.tif"
    },
    "SourceBand": {
     "$": 1
    },
    "SrcRect": {
     "@xOff": 0,
     "@yOff": 0,
     "@xSize": 512,
     "@ySize": 512
    },
    "DstRect": {
     "@xOff": 0,
     "@yOff": 0,
     "@xSize": 512,
     "@ySize": 512
    }
   }
  }
 }
}
```

This allows pygdal-json to JSON-serialize common GDAL operations such as `gdal.Warp` and `gdal.Translate`.

### Usage
##### Python
```python
import gdaljson

#Warp
with open('tests/templates/warped.vrt') as vrtfile:
    vrt = gdaljson.VRTWarpedDataset(vrtfile)
    vrt.warp(clipper='tests/templates/clipper.geojson', cropToCutline=True, dstAlpha=True)
    with open('warp_outfile.vrt', 'wb') as out_vrt:
        vrt.to_xml(out_vrt)

#Translate
with open('tests/templates/translate.vrt') as vrtfile:
    vrt = gdaljson.VRTDataset(vrtfile)
    vrt.warp(bandList=[1,3], srcWin=[0,0,100,100])
    with open('translate_outfile.vrt', 'wb') as out_vrt:
        vrt.to_xml(out_vrt)
```
##### CLI
```commandline
warp <infile.vrt> <outfile.vrt> --opts
translate <infile.vrt> <outfile.vrt> --opts
```
##### Utilities
This library is extended by [pygdal-json-utils](https://github.com/geospatial-jeff/pygdal-json-utils) which contains GDAL utilities for writing VRTs to file.  This library is, by default, not built with `pygdal-json-utils` to isolate the GDAL dependency.

```python
import gdaljson_utils as util
import gdaljson

#Load VRT object to GDAL dataset
out_ds = util.to_gdal(gdaljson.VRTDataset)

#Save VRT object to GTiff
util.to_file(gdaljson.VRTDataset, 'output.tif')
```
Pygdal-json-utils also includes profiles which are used to define primarily GTiff specifications on save.
The base class `util.ImageBase` may be extended to build customized and dynamic GTiff profiles.
See `util.COG` for an example of a COG profile.

```python
#Save to COG
util.to_file(gdaljson.VRTDatset, 'output_cog.tif', profile=util.COG)
```

#### Test Cases
```commandline
python -m unittest tests.test_vrt.VRTTestCases
```


### Resources
- [GDAL VRT Tutorial](https://www.gdal.org/gdal_vrttut.html)
- [VRT XML Schema](https://svn.osgeo.org/gdal/trunk/gdal/data/gdalvrt.xsd)