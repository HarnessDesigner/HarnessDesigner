from typing import Union

import wx


class RealPoint(wx.RealPoint):

    def __init__(self, x: Union[int, float, wx.Point, wx.RealPoint, "RealPoint"],
                 y: int | float | None = None, /, *, z: int | float = None):

        err_msg = f'No matching signature for ({type(x)}, {type(y)}, z={type(z)})'

        if y is None and isinstance(x, (int, float)):
            raise ValueError(err_msg)
        elif not isinstance(x, (int, float)) and y is not None:
            raise ValueError(err_msg)

        if not isinstance(z, (int, float)):
            raise ValueError(err_msg)

        if isinstance(x, (int, float)):
            x = float(x)
            y = float(x)
            wx.RealPoint.__init__(self, float(x), float(y))

        else:
            wx.RealPoint.__init__(self, x)
            x, y = self.Get()

        self._x = x
        self._y = y
        self._z = z

    def GetX(self):
        return self._x

    def GetY(self):
        return self._y

    def GetZ(self):
        return self._z

    def __iter__(self):
        yield self._x
        yield self._y
        yield self._z

    def __str__(self):
        return str(tuple(self))
