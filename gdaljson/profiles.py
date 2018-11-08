from haversine import haversine
import math

class ImageBase(object):

    def __init__(self, data):
        self.data = data

        #Creation options
        self.__compression = None
        self.__zlevel = None
        self.__predictor = None
        self.__blocksize = self.data.blocksize
        self.__tiled = True if self.blocksize[0] == self.blocksize[1] else False

        self.__num_threads = 'ALL_CPUS'
        self.__bigtiff = "IF_SAFER"

    @property
    def predictor(self):
        return self.__predictor

    @predictor.setter
    def predictor(self, value):
        self.__predictor = value

    @property
    def compression(self):
        return self.__compression

    @compression.setter
    def compression(self, value):
        self.__compression = value

    @property
    def zlevel(self):
        return self.__zlevel

    @zlevel.setter
    def zlevel(self, value):
        self.__zlevel = value

    @property
    def blocksize(self):
        return self.__blocksize

    @blocksize.setter
    def blocksize(self, value):
        self.__blocksize = value

    @property
    def bigtiff(self):
        return self.__bigtiff

    @bigtiff.setter
    def bigtiff(self, value):
        self.__bigtiff = value

    @property
    def num_threads(self):
        return self.__num_threads

    @num_threads.setter
    def num_threads(self, value):
        self.__num_threads = value

    @property
    def zoom(self):
        return self.__zoom

    @zoom.setter
    def zoom(self, value):
        self.__zoom = value

    @property
    def resample(self):
        return self.__resample

    @resample.setter
    def resample(self, value):
        self.__resample = value

    @property
    def tiled(self):
        return self.__tiled

    @tiled.setter
    def tiled(self, value):
        self.__tiled = value

    def creation_options(self):
        accepted = ["tiled", "blocksize", "num_threads", "bigtiff", "predictor", "zlevel"]
        creation_list = []
        for item in accepted:
            value = getattr(self, item)
            if value:
                if item == "blocksize":
                    creation_list += [f"BLOCKXSIZE={value}"]
                    creation_list += [f"BLOCKYSIZE={value}"]
                else:
                    value = str(value)
                    creation_list.append(f"{item.upper()}={value.upper()}")
        return creation_list

class Overview():

    def __init__(self, data):
        self.data = data
        self.__resample = None
        self.__zoom = None

        #Config options
        self.__TILED_OVERVIEW = None
        self.__BLOCKXSIZE_OVERVIEW = None
        self.__BLOCKYSIZE_OVERVIEW = None
        self.__COMPRESS_OVERVIEW = None
        self.__PREDICTOR_OVERVIEW = None
        self.__ZLEVEL_OVERVIEW = None

        self.__NUM_THREADS_OVERVIEW = 'ALL_CPUS'

    @property
    def resample(self):
        return self.__resample

    @resample.setter
    def resample(self, value):
        self.__resample = value

    @property
    def zoom(self):
        return math.ceil(
            math.log((2 * math.pi * 6378137) /
                     (self.get_resolution() * 256), 2))

    @property
    def tiled(self):
        return self.__TILED_OVERVIEW

    @tiled.setter
    def tiled(self, value):
        self.__TILED_OVERVIEW = value

    @property
    def blocksize(self):
        return [self.__BLOCKXSIZE_OVERVIEW, self.__BLOCKYSIZE_OVERVIEW]

    @blocksize.setter
    def blocksize(self, value):
        self.__BLOCKXSIZE_OVERVIEW = value[0]
        self.__BLOCKYSIZE_OVERVIEW = value[1]

    @property
    def compression(self):
        return self.__COMPRESS_OVERVIEW

    @compression.setter
    def compression(self, value):
        self.__COMPRESS_OVERVIEW = value

    @property
    def predictor(self):
        return self.__PREDICTOR_OVERVIEW

    @predictor.setter
    def predictor(self, value):
        self.__PREDICTOR_OVERVIEW = value

    @property
    def zlevel(self):
        return self.__ZLEVEL_OVERVIEW

    @zlevel.setter
    def zlevel(self, value):
        self.__ZLEVEL_OVERVIEW = value

    def options(self):
        forbidden = ['_Overview__resample', '_Overview__zoom', 'data']
        opts = {k[11:]:v for (k,v) in self.__dict__.items() if k not in forbidden and v}
        return opts

    def get_resolution(self):
        if self.data.srs.is_geographic:
            extent = self.data.extent
            left = (extent[0], (extent[2]+extent[3])/2)
            right = (extent[1], (extent[2]+extent[3])/2)
            top = ((extent[0]+extent[1])/2, extent[3])
            bottom = ((extent[0]+extent[1])/2, extent[2])
            return max(
                haversine(left, right) * 1000 / self.data.shape[0],
                haversine(top, bottom) * 1000 / self.data.shape[1]
            )
        else:
            return max(self.data.xres, self.data.yres)

    def overviews(self):
        shape = self.data.shape
        overviews = []
        for i in range(1, self.zoom):
            overviews.append(2**i)
            if (shape[1] / 2**i) < int(self.blocksize[0]) and (shape[0] / 2**i) < int(self.blocksize[1]):
                break
        return overviews

class COG(ImageBase):

    def __init__(self, data):
        ImageBase.__init__(self, data)

        #Configurating image
        self.tiled = True
        self.blocksize = '512'
        self.set_predictor()
        self.set_compression()

        #Configurating overviews
        self.overview = Overview(data)
        self.configure_overviews()

    def set_predictor(self):
        if 'Int' in self.data.bitdepth:
            self.predictor = '2'
        elif 'Float' in self.data.bitdepth:
            self.predictor = '3'

    def set_compression(self):
        if self.data.bitdepth is 'Byte':
            self.compression = 'JPEG'
        else:
            self.compression = 'DEFLATE'
            self.zlevel = '9'

    def configure_overviews(self):
        self.overview.tiled = 'YES'
        self.overview.blocksize = [self.blocksize, self.blocksize]
        self.overview.compression = self.compression
        self.overview.predictor = self.predictor
        self.overview.zlevel = self.zlevel
        self.overview.resample = 'LANCZOS'