
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

        self.__copy_src_overviews = None
        self.__resample = None
        self.__zoom = None

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
    def copy_src_overviews(self):
        return self.__copy_src_overviews

    @copy_src_overviews.setter
    def copy_src_overviews(self, value):
        self.__copy_src_overviews = value

    @property
    def tiled(self):
        return self.__tiled

    @tiled.setter
    def tiled(self, value):
        self.__tiled = value

    def creation_options(self):
        accepted = ["tiled", "blocksize", "num_threads", "bigtiff", "predictor", "zlevel", "copy_src_overviews"]
        creation_list = []
        for item in accepted:
            value = getattr(self, item)
            if value:
                if item == "blocksize":
                    creation_list += [f"BLOCKXSIZE={value[0]}"]
                    creation_list += [f"BLOCKYSIZE={value[1]}"]
                else:
                    value = str(value)
                    creation_list.append(f"{item.upper()}={value.upper()}")
        return creation_list

    def normal_arguments(self):
        pass

