from typing import Iterable as _Iterable
import math

from . import point as _point
from ..wrappers.decimal import Decimal as _decimal
from .constants import ZERO_5
from . import rotation as _rotation


class Line:

    def __init__(self, p1: _point.Point,
                 p2: _point.Point | None = None,
                 length: _decimal | None = None,
                 x_angle: _decimal | None = None,
                 y_angle: _decimal | None = None,
                 z_angle: _decimal | None = None):

        self._p1 = p1

        if p2 is None:
            if None in (length, x_angle, y_angle, z_angle):
                raise ValueError('If an end point is not supplied then the "length", '
                                 '"x_angle", "y_angle" and "z_angle" parameters need to be supplied')

            p2 = _point.Point(length, _decimal(0.0), _decimal(0.0))
            p2 += p1

            p2.set_angles(x_angle, y_angle, z_angle, p1)

        self._p2 = p2

    def copy(self) -> "Line":
        p1 = self._p1.copy()
        p2 = self._p2.copy()
        return Line(p1, p2)

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @property
    def p2(self) -> _point.Point:
        return self._p2

    def __len__(self) -> int:
        x = self._p2.x - self._p1.x
        y = self._p2.y - self._p1.y
        z = self._p2.z - self._p1.z
        res = math.sqrt(x * x + y * y + z * z)
        return int(round(res))

    def length(self) -> _decimal:
        x = self._p2.x - self._p1.x
        y = self._p2.y - self._p1.y
        z = self._p2.z - self._p1.z

        return _decimal(math.sqrt(x * x + y * y + z * z))

    def get_x_angle(self) -> _decimal:
        return _rotation.get_angles(self._p1, self._p2)[0]

    def get_y_angle(self) -> _decimal:
        return _rotation.get_angles(self._p1, self._p2)[1]

    def get_z_angle(self) -> _decimal:
        return _rotation.get_angles(self._p1, self._p2)[2]

    def get_angles(self):
        return _rotation.get_angles(self._p1, self._p2)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal,
                   origin: _point.Point | None = None) -> None:

        if origin is None:
            origin = self.center

        if origin != self.p1 and origin != self.p2:
            self.p1.set_angles(x_angle, y_angle, z_angle, origin)
            self.p2.set_angles(x_angle, y_angle, z_angle, origin)
        elif origin != self.p1:
            self.p1.set_angles(x_angle, y_angle, z_angle, origin)
        else:
            self.p2.set_angles(x_angle, y_angle, z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: _point.Point | None = None) -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point | None = None) -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: _point.Point | None = None) -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    def point_from_start(self, distance: _decimal) -> _point.Point:
        line = Line(self.p1.copy(), None, distance, *self.get_angles())
        return line.p2

    @property
    def center(self) -> _point.Point:
        x = (self._p1.x + self._p2.x) * ZERO_5
        y = (self._p1.y + self._p2.y) * ZERO_5
        z = (self._p1.z + self._p2.z) * ZERO_5
        return _point.Point(x, y, z)

    def __iter__(self) -> _Iterable[_point.Point]:
        return iter([self._p1, self._p2])
