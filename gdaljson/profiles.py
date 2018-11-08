from haversine import haversine
import math

class ImageBase(object):

    def __init__(self, data):
        self.data = data

        #Creation options
        self.__COMPRESS = None
        self.__ZLEVEL = None
        self.__PREDICTOR = None
        self.__BLOCKXSIZE = self.data.blocksize[0]
        self.__BLOCKYSIZE = self.data.blocksize[1]
        self.__TILED = "TRUE" if self.blocksize[0] == self.blocksize[1] else "FALSE"

        self.__NUM_THREADS = 'ALL_CPUS'
        self.__BIGTIFF = "IF_SAFER"

    @property
    def predictor(self):
        return self.__PREDICTOR

    @predictor.setter
    def predictor(self, value):
        self.__PREDICTOR = value

    @property
    def compression(self):
        return self.__COMPRESS

    @compression.setter
    def compression(self, value):
        self.__COMPRESS = value

    @property
    def zlevel(self):
        return self.__ZLEVEL

    @zlevel.setter
    def zlevel(self, value):
        self.__ZLEVEL = value

    @property
    def blocksize(self):
        return [self.__BLOCKXSIZE, self.__BLOCKYSIZE]

    @blocksize.setter
    def blocksize(self, value):
        self.__BLOCKXSIZE = value[0]
        self.__BLOCKYSIZE = value[1]

    @property
    def bigtiff(self):
        return self.__BIGTIFF

    @bigtiff.setter
    def bigtiff(self, value):
        self.__BIGTIFF = value

    @property
    def num_threads(self):
        return self.__NUM_THREADS

    @num_threads.setter
    def num_threads(self, value):
        self.__NUM_THREADS = value

    @property
    def tiled(self):
        return self.__TILED

    @tiled.setter
    def tiled(self, value):
        self.__TILED = value

    def creation_options(self):
        # accepted = ["COMPRESSION", "ZLEVEL"]
        opts = {k.split('__')[-1]:v for (k,v) in self.__dict__.items() if 'ImageBase' in k and v}
        return [f'{k}={v}' for k,v in opts.items()]

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
    def ovr_resample(self):
        return self.__resample

    @ovr_resample.setter
    def ovr_resample(self, value):
        self.__resample = value

    @property
    def zoom(self):
        return math.ceil(
            math.log((2 * math.pi * 6378137) /
                     (self.get_resolution() * 256), 2))

    @property
    def ovr_tiled(self):
        return self.__TILED_OVERVIEW

    @ovr_tiled.setter
    def ovr_tiled(self, value):
        self.__TILED_OVERVIEW = value

    @property
    def ovr_blocksize(self):
        return [self.__BLOCKXSIZE_OVERVIEW, self.__BLOCKYSIZE_OVERVIEW]

    @ovr_blocksize.setter
    def ovr_blocksize(self, value):
        self.__BLOCKXSIZE_OVERVIEW = value[0]
        self.__BLOCKYSIZE_OVERVIEW = value[1]

    @property
    def ovr_compression(self):
        return self.__COMPRESS_OVERVIEW

    @ovr_compression.setter
    def ovr_compression(self, value):
        self.__COMPRESS_OVERVIEW = value

    @property
    def ovr_predictor(self):
        return self.__PREDICTOR_OVERVIEW

    @ovr_predictor.setter
    def ovr_predictor(self, value):
        self.__PREDICTOR_OVERVIEW = value

    @property
    def ovr_zlevel(self):
        return self.__ZLEVEL_OVERVIEW

    @ovr_zlevel.setter
    def ovr_zlevel(self, value):
        self.__ZLEVEL_OVERVIEW = value

    def overview_options(self):
        opts = {k.split('__')[-1]:v for (k,v) in self.__dict__.items() if 'Overview' in k and v}
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

class COG(ImageBase, Overview):

    def __init__(self, data):
        ImageBase.__init__(self, data)

        #Configurating image
        self.tiled = "TRUE"
        self.blocksize = ['512', '512']
        self.set_predictor()
        self.set_compression()

        #Configurating overviews
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
        self.ovr_tiled = 'YES'
        self.ovr_blocksize = self.blocksize
        self.ovr_compression = self.compression
        self.ovr_predictor = self.predictor
        self.ovr_zlevel = self.zlevel
        self.ovr_resample = 'LANCZOS'