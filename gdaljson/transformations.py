from xmljson import badgerfish as bf
import xml.etree.ElementTree as ET
import xml.dom.minidom as md


def dumps(d, pretty=False):
    """Dump from dict (json) to xml"""
    vrtxml = ET.tostring(bf.etree(d)[0])
    if pretty:
        return md.parseString(vrtxml)
    return vrtxml

def loads(s):
    """Load dict(json) from xml string"""
    return dict(bf.data(ET.fromstring(s)))