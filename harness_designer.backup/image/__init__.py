from typing import TYPE_CHECKING

import sys
import os
import wx

from . import utils


BASE_PATH = os.path.dirname(__file__)


class Image:

    def __init__(self, path=None, png_data=None):
        self._path = path
        self._png_data = png_data

    @property
    def png_data(self):
        if self._png_data is not None:
            return self._png_data

        with open(self._path, 'rb') as f:
            return f.read()

    @property
    def bitmap(self) -> wx.Bitmap:
        return wx.Bitmap.FromPNGData(self.png_data)

    @property
    def disabled_bitmap(self) -> wx.Bitmap:
        bmp = wx.Bitmap.FromPNGData(self.png_data)
        bmp.ConvertToDisabled()
        return bmp

    @property
    def image(self) -> wx.Image:
        return utils.wx_bitmap_2_wx_image(wx.Bitmap.FromPNGData(self.png_data))

    @property
    def cursor(self) -> wx.Cursor:
        image = utils.wx_bitmap_2_wx_image(wx.Bitmap.FromPNGData(self.png_data))
        return utils.wx_image_2_wx_cursor(image)

    def resize(self, w: int, h: int) -> "Image":
        bmp = utils.resize_wx_bitmap(self.bitmap, w, h)
        return Image(png_data=utils.wx_bitmap_2_png_bytes(bmp))

    def rotate(self, angle: int | float) -> "Image":
        bmp = utils.rotate_wx_bitmap(self.bitmap, angle)
        return Image(png_data=utils.wx_bitmap_2_png_bytes(bmp))

    def recolor(self, r, g, b):
        img = utils.bytes_data_2_pil_image(self.png_data)

        w, h = img.size
        for y in range(h):
            for x in range(w):
                a = img.getpixel((x, y))[-1]
                img.putpixel((x, y), (r, g, b, a))

        res = Image(png_data=utils.pil_image_2_png_bytes(img))
        img.close()
        return res

    def __add__(self, other: "Image") -> "Image":
        dc = wx.MemoryDC()
        bmp1 = self.bitmap
        dc.SelectObject(bmp1)

        w1, h1 = bmp1.GetSize()

        bmp2 = other.bitmap
        w2, h2 = bmp2.GetSize()

        if w1 != w2:
            x_offset = int((w1 - w2) / 2)
        else:
            x_offset = 0

        if h1 != h2:
            y_offset = int((h1 - h2) / 2)
        else:
            y_offset = 0

        gcdc = wx.GCDC(dc)

        gcdc.DrawBitmap(bmp2, x_offset, y_offset)
        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

        return Image(png_data=utils.wx_bitmap_2_png_bytes(bmp1))


# This is a dynamic loader that acts like a module.
# This is done to save some memory by only loading the icons and images that
# are actually being used
class ImageLoader:

    def __init__(self, path):
        mod = sys.modules[__name__]

        if path == BASE_PATH:
            self.__dict__['__name__'] = __name__
            self.__dict__['__file__'] = mod.__file__
            self.__dict__['__package__'] = mod.__package__
            self.__dict__['__doc__'] = mod.__doc__
            self.__dict__['__loader__'] = mod.__loader__
            self.__dict__['__spec__'] = mod.__spec__
            self.__dict__['__path__'] = mod.__path__
            self.__dict__['___cached__'] = mod.__cached__

            sys.modules[__name__] = self
        else:
            self.__name__ = os.path.split(path)[-1]

        self.__dict__['__original_module__'] = mod

        self.__base_path__ = path

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        if hasattr(self.__original_module__, item):
            return getattr(self.__original_module__, item)

        path_ = os.path.join(self.__base_path__, item)

        if os.path.isdir(path_):
            attr = ImageLoader(path_)
            setattr(self, item, attr)
            return attr

        path_ += '.png'

        if os.path.exists(path_):
            attr = Image(path_)
            setattr(self, item, attr)
            return attr

        raise AttributeError(item)


__base = ImageLoader(BASE_PATH)


if TYPE_CHECKING:

    class cursors(ImageLoader):
        back_angle: Image = ...
        forward_angle: Image = ...
        left_bottom_corner_rotate: Image = ...
        left_right: Image = ...
        left_top_corner_rotate: Image = ...
        move: Image = ...
        pointer: Image = ...
        right_bottom_corner_rotate: Image = ...
        right_top_corner_rotate: Image = ...
        rotate: Image = ...
        up_down: Image = ...

    class icons(ImageLoader):
        circle: Image = ...
        crop: Image = ...
        orb: Image = ...
        pencil: Image = ...
        settings: Image = ...
        square: Image = ...
        bundle_cover: Image = ...
        connector: Image = ...
        cpa_lock: Image = ...
        seal: Image = ...
        splice: Image = ...
        terminal: Image = ...
        tpa_lock: Image = ...
        transition: Image = ...
        wire: Image = ...
