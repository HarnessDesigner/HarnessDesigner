# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import weakref
import colorsys
from PySide6.QtGui import QColor as _QColor


class ColorMeta(type):
    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in list(cls._instances.items()):
            if value == ref:
                del cls._instances[key]
                return

    def __call__(cls, r: float | int, g: float | int, b: float | int,
                 a: float | int = 255, db_id: str | None = None) -> "Color":

        if db_id is not None:
            if db_id not in cls._instances:
                instance = type.__call__(cls, r, g, b, a, db_id)
                cls._instances[db_id] = weakref.ref(
                    instance, cls._remove_ref
                )
            elif cls._instances[db_id]() is None:
                # Handle edge case where a reference has been removed
                # but the reference object has not yet been removed from
                # the dict. We have to make sure that we delete the key
                # before adding the object again because of the internal
                # mechanics in weakref and not wanting it to remove
                # the newly added reference
                del cls._instances[db_id]
                instance = type.__call__(cls, r, g, b, a, db_id)
                cls._instances[db_id] = weakref.ref(
                    instance, cls._remove_ref
                )
            else:
                instance = cls._instances[db_id]()
        else:
            instance = type.__call__(cls, r, g, b, a, db_id)

        return instance


class Color(metaclass=ColorMeta):
    """
    A framework-agnostic RGBA colour class with a weak-ref singleton cache
    (keyed by db_id) and an observer/callback system.

    Replaces the previous wx.Colour subclass. Internally stores r, g, b, a as
    plain Python ints (0-255). Exposes the same public API as before so that
    the rest of the codebase requires no changes:

        GetRed / GetGreen / GetBlue / GetAlpha
        GetRGBA / Set / SetRGB / SetRGBA
        rgb / rgba properties (int tuples)
        rgb_scalar / rgba_scalar properties (float tuples)
        GetLighterColor / GetDarkerColor
        to_qcolor()          — new helper, returns a QColor for Qt widgets
    """

    __slots__ = (
        'db_id',
        '_r', '_g', '_b', '_a',
        '_callbacks',
        '_ref_count',
    )

    def __init__(self, r: int | float, g: int | float,
                 b: int | float, a: int | float = 255,
                 db_id: str | None = None):

        self.db_id = db_id

        self._r, self._g, self._b, self._a = [
            int(round(item * 255.0)) if isinstance(item, float) else int(item)
            for item in (r, g, b, a)
        ]

        self._callbacks = []
        self._ref_count = 0

    # ------------------------------------------------------------------
    # Context manager (ref-counting batched updates)
    # ------------------------------------------------------------------

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    # ------------------------------------------------------------------
    # Callback management (mirrors the original bind/unbind interface)
    # ------------------------------------------------------------------

    def __remove_callback(self, ref):
        try:
            self._callbacks.remove(ref)
        except Exception:  # NOQA
            pass

    def bind(self, callback):
        ref = weakref.WeakMethod(callback, self.__remove_callback)
        self._callbacks.append(ref)

    def unbind(self, callback):
        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
            elif cb == callback:
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
                self._callbacks.remove(ref)

    # ------------------------------------------------------------------
    # wx.Colour-compatible getters
    # ------------------------------------------------------------------

    def GetRed(self) -> int:
        return self._r

    def GetGreen(self) -> int:
        return self._g

    def GetBlue(self) -> int:
        return self._b

    def GetAlpha(self) -> int:
        return self._a

    def GetRGBA(self) -> int:
        """Returns a single packed 32-bit RGBA integer (r<<24|g<<16|b<<8|a)."""
        return (self._r << 24) | (self._g << 16) | (self._b << 8) | self._a

    def IsOk(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # wx.Colour-compatible setters
    # ------------------------------------------------------------------

    def Set(self, *RGBA):
        if len(RGBA) == 1:
            val = RGBA[0]
            self._r = (val >> 24) & 0xFF
            self._g = (val >> 16) & 0xFF
            self._b = (val >> 8) & 0xFF
            self._a = val & 0xFF
            self._process_update()

        elif len(RGBA) == 3:
            self._r, self._g, self._b = [
                int(item * 255) if isinstance(item, float) else int(item)
                for item in RGBA
            ]
            self._process_update()

        elif len(RGBA) == 4:
            self._r, self._g, self._b, self._a = [
                int(item * 255) if isinstance(item, float) else int(item)
                for item in RGBA
            ]
            self._process_update()

        else:
            raise ValueError(f'Set() expects 1, 3 or 4 arguments, got {len(RGBA)}')

    def SetRGBA(self, *RGBA):
        if len(RGBA) == 1:
            val = RGBA[0]
            self._r = (val >> 24) & 0xFF
            self._g = (val >> 16) & 0xFF
            self._b = (val >> 8) & 0xFF
            self._a = val & 0xFF
            self._process_update()

        elif len(RGBA) == 4:
            self._r, self._g, self._b, self._a = [
                int(item * 255) if isinstance(item, float) else int(item)
                for item in RGBA
            ]
            self._process_update()

        else:
            raise ValueError(f'SetRGBA() expects 1 or 4 arguments, got {len(RGBA)}')

    def SetRGB(self, *RGB):
        if len(RGB) == 1:
            val = RGB[0]
            self._r = (val >> 16) & 0xFF
            self._g = (val >> 8) & 0xFF
            self._b = val & 0xFF
            self._process_update()

        elif len(RGB) == 3:
            self._r, self._g, self._b = [
                int(item * 255) if isinstance(item, float) else int(item)
                for item in RGB
            ]
            self._process_update()

        else:
            raise ValueError(f'SetRGB() expects 1 or 3 arguments, got {len(RGB)}')

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rgb_scalar(self) -> tuple[float, float, float]:
        return self._r / 255.0, self._g / 255.0, self._b / 255.0

    @property
    def rgba_scalar(self) -> tuple[float, float, float, float]:
        return self._r / 255.0, self._g / 255.0, self._b / 255.0, self._a / 255.0

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        return self._r, self._g, self._b, self._a

    @rgba.setter
    def rgba(self, value: tuple[int, int, int, int]):
        r, g, b, a = value
        self.SetRGBA(r, g, b, a)

    @property
    def rgb(self) -> tuple[int, int, int]:
        return self._r, self._g, self._b

    @rgb.setter
    def rgb(self, value: tuple[int, int, int]):
        r, g, b = value
        self.rgba = (r, g, b, self._a)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __int__(self):
        return self.GetRGBA()

    def __repr__(self):
        return (f'Color(r={self._r}, g={self._g}, b={self._b}, a={self._a}'
                + (f', db_id={self.db_id!r}' if self.db_id else '') + ')')

    def __eq__(self, other):
        if isinstance(other, Color):
            return (self._r, self._g, self._b, self._a) == (other._r, other._g, other._b, other._a)
        return NotImplemented

    def __hash__(self):
        return hash((self._r, self._g, self._b, self._a))

    # ------------------------------------------------------------------
    # Static / class helpers
    # ------------------------------------------------------------------

    @staticmethod
    def from_int(rgba: int) -> "Color":
        r = (rgba >> 24) & 0xFF
        g = (rgba >> 16) & 0xFF
        b = (rgba >> 8) & 0xFF
        a = rgba & 0xFF
        return Color(r, g, b, a)

    # ------------------------------------------------------------------
    # Colour manipulation
    # ------------------------------------------------------------------

    def GetLighterColor(self, percentage=25) -> "Color":
        a = self._a
        h, s, v = colorsys.rgb_to_hsv(*self.rgb_scalar)
        v += v * (percentage / 100.0)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return Color(
            min(255, int(round(r * 255))),
            min(255, int(round(g * 255))),
            min(255, int(round(b * 255))),
            a
        )

    def GetDarkerColor(self, percentage=25) -> "Color":
        a = self._a
        h, s, v = colorsys.rgb_to_hsv(*self.rgb_scalar)
        v -= v * (percentage / 100.0)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return Color(
            min(255, int(round(r * 255))),
            min(255, int(round(g * 255))),
            min(255, int(round(b * 255))),
            a
        )

    # ------------------------------------------------------------------
    # Qt interop helper
    # ------------------------------------------------------------------

    def to_qcolor(self) -> _QColor:
        """Return a PySide6 QColor equivalent of this Color."""
        return _QColor(self._r, self._g, self._b, self._a)

    @staticmethod
    def from_qcolor(qc: _QColor, db_id: str | None = None) -> "Color":
        """Construct a Color from a PySide6 QColor."""
        return Color(qc.red(), qc.green(), qc.blue(), qc.alpha(), db_id)
