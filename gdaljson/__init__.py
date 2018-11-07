from .raster import Raster

def dumps(d, pretty=False):
    """Dump from dict (json) to xml"""
    from xmljson import badgerfish as bf
    import xml.etree.ElementTree as ET
    vrtxml = ET.tostring(bf.etree(d)[0])
    if pretty:
        import xml.dom.minidom as md
        return md.parseString(vrtxml)
    return vrtxml

def loads(s):
    """Load dict(json) from xml string"""
    from xmljson import badgerfish as bf
    import xml.etree.ElementTree as ET
    return dict(bf.data(ET.fromstring(s)))