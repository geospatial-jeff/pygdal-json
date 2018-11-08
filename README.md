# pygdal-json

A simple Python module for JSON-encoding the GDAL Data Model.

### GDAL VRT Format
GDAL's VRT driver is a format driver for GDAL that allows a virtual GDAL dataset to be composed from other GDAL datasets with repositioning, and algorithms potentially applied as well as various kinds of metadata altered or added.  VRT descriptions of datasets can be saved in an XML format normally given the extension `.vrt`.  An exapmle of a simple .vrt file referring to a 512x512 dataset with one-band loaded from utm.tif might look like:

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

### Resources
- [GDAL VRT Tutorial](https://www.gdal.org/gdal_vrttut.html)
- [VRT XML Schema](https://svn.osgeo.org/gdal/trunk/gdal/data/gdalvrt.xsd)