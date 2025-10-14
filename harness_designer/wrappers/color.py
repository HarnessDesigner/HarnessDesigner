from typing import Callable

import wx
import weakref
import colorsys


class Color(wx.Colour):

    def __init__(self, r: int | float, g: int | float,
                 b: int | float, a: int | float = 255):

        r, g, b, a = [int(round(item * 255.0)) if isinstance(item, float) else item
                      for item in [r, g, b, a]]

        wx.Colour.__init__(self, r, g, b, a)

        self._callbacks = []

    @property
    def matplotlib(self) -> tuple[float, float, float, float]:
        r, g, b, a = [item / 255.0 for item in self.GetRGBA()]

        return r, g, b, a

    @property
    def numpy(self) -> tuple[float, float, float, float]:
        return self.matplotlib

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        r, g, b, a = self.GetRGBA()
        return r, g, b, a

    @rgba.setter
    def rgba(self, value: tuple[int, int, int, int]):
        r, g, b, a = value
        self.SetRGBA((r, g, b, a))

        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(ref)
            else:
                func()

    @property
    def rgb(self) -> tuple[int, int, int]:
        r, g, b = self.GetRGB()
        return r, g, b

    @rgb.setter
    def rgb(self, value: tuple[int, int, int]):
        a = self.GetRGBA()[-1]
        r, g, b = value
        self.SetRGBA((r, g, b, a))

        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(ref)
            else:
                func()

    def __remove_cb(self, ref):
        try:
            self._callbacks.remove(ref)
        except ValueError:
            pass

    def Bind(self, cb: Callable[[None], None]) -> None:
        ref = weakref.WeakMethod(cb, self.__remove_cb)
        self._callbacks.append(ref)

    def UnBind(self, cb: Callable[[None], None]) -> None:
        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(func)
            elif func == cb:
                self._callbacks.remove(func)
                break

    def __int__(self):
        r, g, b, a = self.GetRGBA()
        return r << 24 | g << 16 | b << 8 | a

    @staticmethod
    def from_int(rgba: int) -> "Color":
        r = (rgba >> 24) & 0xFF
        g = (rgba >> 16) & 0xFF
        b = (rgba >> 8) & 0xFF
        a = rgba & 0xFF

        return Color(r, g, b, a)

    def GetLighterColor(self, percentage=25):
        a = self.GetRGBA()[-1]
        h, s, v = colorsys.rgb_to_hsv(*self.matplotlib[:-1])

        percentage /= 100.0
        v += v * percentage
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        return Color(r, g, b, a)

    def GetDarkerColor(self, percentage=25):
        a = self.GetRGBA()[-1]
        h, s, v = colorsys.rgb_to_hsv(*self.matplotlib[:-1])

        percentage /= 100.0
        v -= v * percentage
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        return Color(r, g, b, a)
