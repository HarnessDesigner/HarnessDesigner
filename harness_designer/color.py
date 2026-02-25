import wx
import weakref
import colorsys


class ColorMeta(type(wx.Colour)):
    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, r: float | int, g: float | int, b: float | int,
                 a: float | int = 255, db_id: str | None = None) -> "Color":

        if db_id is not None:
            if db_id not in cls._instances:
                instance = type.__call__(cls, r, g, b, a, db_id)
                cls._instances[db_id] = weakref.ref(instance)

            elif cls._instances[db_id]() is None:
                # Handle edge case where a reference has been removed
                # but the reference object has not yet been removed from
                # the dict. We have to make sure that we delete the key
                # before adding the object again because of the internal
                # mechanics in weakref and not wanting it to remove
                # the newly added reference
                del cls._instances[db_id]
                instance = type.__call__(cls, r, g, b, a, db_id)
                cls._instances[db_id] = weakref.ref(instance)
            else:
                instance = cls._instances[db_id]()
        else:
            instance = type.__call__(cls, r, g, b, a, db_id)

        return instance


class Color(wx.Colour, metaclass=ColorMeta):

    def __init__(self, r: int | float, g: int | float,
                 b: int | float, a: int | float = 255,
                 db_id: str | None = None):

        self.db_id = db_id

        r, g, b, a = [int(round(item * 255.0)) if isinstance(item, float) else item
                      for item in [r, g, b, a]]

        wx.Colour.__init__(self, r, g, b, a)

        self._callbacks = []
        self._ref_count = 0

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def __remove_callback(self, ref):
        try:
            self._callbacks.remove(ref)
        except:  # NOQA
            pass

    def bind(self, callback):
        # we don't explicitly check to see if a callback is already registered
        # what we care about is if a callback is called only one time and that
        # check is done when the callbacks are being done and if there happend
        # to be a duplicate the duplicate is then removed at that point in time.
        ref = weakref.WeakMethod(callback, self.__remove_callback)

        self._callbacks.append(ref)

    def unbind(self, callback):
        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
            elif cb == callback:
                # we don't return after locating a matching callback in the
                # event a callback was registered more than one time. duplicates
                # are also removed aty the time callbacks get called but if an update
                # to a point never occurs we want to make sure that we explicitly
                # unbind all callbacks including duplicates.
                self._callbacks.remove(ref)

    def _process_update(self):
        if self._ref_count:
            return

        used_callbacks = []
        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
            elif cb not in used_callbacks:
                cb(self)
                used_callbacks.append(cb)
            else:
                # remove duplicate callbacks since we are
                # iterating over the callbacks
                self._callbacks.remove(ref)

    def Set(self, *RGBA):
        if len(RGBA) == 1:
            RGBA = RGBA[0]

            r = RGBA >> 24
            g = (RGBA >> 16) & 0xFF
            b = (RGBA >> 8) & 0xFF
            a = RGBA & 0xFF

            wx.Colour.Set(self, r, g, b, a)
            self._process_update()
        elif len(RGBA) == 3:
            r, g, b = [int(item * 255) if isinstance(item, float) else item for item in RGBA]
            a = self.GetAlpha()
            wx.Colour.Set(self, r, g, b, a)
            self._process_update()

        elif len(RGBA) == 4:
            r, g, b, a = [int(item * 255) if isinstance(item, float) else item for item in RGBA]
            wx.Colour.Set(self, r, g, b, a)
            self._process_update()

        else:
            raise ValueError

    def SetRGBA(self, *RGBA):
        if len(RGBA) == 1:
            RGBA = RGBA[0]

            r = RGBA >> 24
            g = (RGBA >> 16) & 0xFF
            b = (RGBA >> 8) & 0xFF
            a = RGBA & 0xFF

            wx.Colour.Set(self, r, g, b, a)
            self._process_update()

        elif len(RGBA) == 4:
            r, g, b, a = [int(item * 255) if isinstance(item, float) else item
                          for item in RGBA]
            wx.Colour.Set(self, r, g, b, a)
            self._process_update()

        else:
            raise ValueError

    def SetRGB(self, *RGB):
        if len(RGB) == 1:
            RGB = RGB[0]

            r = RGB >> 16
            g = (RGB >> 8) & 0xFF
            b = RGB & 0xFF

            wx.Colour.Set(self, r, g, b)
            self._process_update()

        elif len(RGB) == 3:
            r, g, b = [int(item * 255) if isinstance(item, float) else item for
                       item in RGB]

            wx.Colour.Set(self, r, g, b)
            self._process_update()

        else:
            raise ValueError

    @property
    def rgb_scalar(self) -> tuple[float, float, float]:
        r, g, b = [item / 255.0 for item in (self.GetRed(), self.GetGreen(), self.GetBlue())]

        return r, g, b

    @property
    def rgba_scalar(self) -> tuple[float, float, float, float]:
        r, g, b, a = [item / 255.0 for item in
                      (self.GetRed(), self.GetGreen(), self.GetBlue(), self.GetAlpha())]

        return r, g, b, a

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        r, g, b, a = self.GetRed(), self.GetGreen(), self.GetBlue(), self.GetAlpha()
        return r, g, b, a

    @rgba.setter
    def rgba(self, value: tuple[int, int, int, int]):
        r, g, b, a = value
        self.SetRGBA(r, g, b, a)

    @property
    def rgb(self) -> tuple[int, int, int]:
        r, g, b = self.GetRed(), self.GetGreen(), self.GetBlue()
        return r, g, b

    @rgb.setter
    def rgb(self, value: tuple[int, int, int]):
        a = self.GetAlpha()
        r, g, b = value

        self.rgba = (r, g, b, a)

    def __int__(self):
        return self.GetRGBA()

    @staticmethod
    def from_int(rgba: int) -> "Color":
        r = (rgba >> 24) & 0xFF
        g = (rgba >> 16) & 0xFF
        b = (rgba >> 8) & 0xFF
        a = rgba & 0xFF

        return Color(r, g, b, a)

    def GetLighterColor(self, percentage=25):
        a = self.GetAlpha()
        h, s, v = colorsys.rgb_to_hsv(*self.rgb_scalar)

        percentage /= 100.0
        v += v * percentage
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        return Color(min(255, int(round(r * 255))), min(255, int(round(g * 255))),
                     min(0, int(round(b * 255))), a)

    def GetDarkerColor(self, percentage=25):
        a = self.GetAlpha()
        h, s, v = colorsys.rgb_to_hsv(*self.rgb_scalar)

        percentage /= 100.0
        v -= v * percentage
        r, g, b = colorsys.hsv_to_rgb(h, s, v)

        return Color(min(255, int(round(r * 255))), min(255, int(round(g * 255))),
                     min(255, int(round(b * 255))), a)
