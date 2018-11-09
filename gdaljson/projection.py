import json
import os

wkt = json.loads(open(os.path.join(os.path.split(os.path.realpath(__file__))[0], 'projections/gdal_epsg.json')).read())

class SpatialRef():

    def __init__(self, wkt_string):
        self.epsg = wkt_string.split(",")[-1][1:-3]
        self.wkt = wkt[self.epsg][0]

    @property
    def linearunit(self):
        return self.wkt.split("UNIT")[-1].split('"')[1]

    @property
    def is_geographic(self):
        if self.wkt.startswith('GEOGCS'):
            return True
        return False