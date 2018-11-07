from osgeo import osr

class SpatialRef():

    @staticmethod
    def _define_projection(wkt_string):
        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt_string)
        return srs

    def __init__(self, wkt_string):
        self.srs = self._define_projection(wkt_string)

    @property
    def epsg(self):
        if self.srs.IsProjected():
            return int(self.srs.GetAttrValue('AUTHORITY', 1))
        elif self.srs.IsGeographic():
            epsg_code = self.srs.GetAttrValue('AUTHORITY', 1)
            proj_string = self.srs.ExportToWkt()
            if not epsg_code:
                if 'WGS_84' in proj_string:
                    return 4326
                elif 'North_American_1983' in proj_string:
                    return 4269
                else:
                    print("WARNING: EPSG CODE NOT RECOGNIZED")
            return int(epsg_code)

    @property
    def linearunit(self):
        return self.srs.GetLinearUnitsName()

    @property
    def is_geographic(self):
        return self.srs.IsGeographic()

    @property
    def is_projected(self):
        return self.srs.IsProjected()

    def IsSame(self, srs):
        return self.srs.IsSame(srs.srs)

    def ExportToWkt(self):
        return self.srs.ExportToWkt()

    def ExportToXML(self):
        return self.srs.ExportToXML()

    def ExportToProj4(self):
        return self.srs.ExportToProj4()

