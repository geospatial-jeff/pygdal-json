import requests

class SpatialRef():

    def __init__(self, wkt_string):
        self.epsg = wkt_string.split(",")[-1][1:-3]
        self.wkt = wkt(self.epsg)

    @property
    def linearunit(self):
        return self.wkt.split("UNIT")[-1].split('"')[1]

    @property
    def is_geographic(self):
        if self.wkt.startswith('GEOGCS'):
            return True
        return False

def wkt(epsg):
    url = f'http://epsg.io/?q={epsg}&format=json'
    resp = requests.get(url)
    data = resp.json()
    return data['results'][0]['wkt']