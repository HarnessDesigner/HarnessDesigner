from typing import Iterable as _Iterable
import math

import numpy as np

from . import point as _point
from ..wrappers.decimal import Decimal as _decimal
from .constants import ZERO_5
from . import angle as _angle


class Line:

    def __init__(self, p1: _point.Point,
                 p2: _point.Point | None = None,
                 length: _decimal | None = None,
                 angle: _angle.Angle | None = None):

        self._p1 = p1

        if p2 is None:
            if None in (length, angle):
                raise ValueError('If an end point is not supplied then the "length", '
                                 '"x_angle", "y_angle" and "z_angle" parameters need to be supplied')

            p2 = _point.Point(length, _decimal(0.0), _decimal(0.0))
            p2 @= angle
            p2 += p1

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

    def get_angle(self, origin: _point.Point) -> _angle.Angle:
        temp_p1 = self._p1.copy()
        temp_p2 = self._p2.copy()

        if origin == self._p1:
            temp_p2 -= temp_p1
            temp_p1 = _point.ZERO_POINT
        elif origin == self._p2:
            temp_p1 -= temp_p2
            temp_p2 = _point.ZERO_POINT
        else:
            temp_p1 -= origin
            temp_p2 -= origin

        return _angle.Angle(temp_p1, temp_p2)

    def set_angle(self, angle: _angle.Angle, origin: _point.Point) -> None:
        if origin == self._p1:
            temp_p2 = self._p2.copy()
            temp_p2 -= origin
            temp_p2 @= angle
            temp_p2 += origin
            diff = temp_p2 - self._p2
            self._p2 += diff

        elif origin == self._p2:
            temp_p1 = self._p1.copy()
            temp_p1 -= origin
            temp_p1 @= angle
            temp_p1 += origin
            diff = temp_p1 - self._p1
            self._p1 += diff
        else:
            temp_p1 = self._p1.copy()
            temp_p2 = self._p2.copy()

            temp_p1 -= origin
            temp_p2 -= origin

            temp_p1 @= angle
            temp_p2 @= angle

            temp_p1 += origin
            temp_p2 += origin

            diff_p1 = temp_p1 - self._p1
            diff_p2 = temp_p2 - self._p2

            self._p1 += diff_p1
            self._p2 += diff_p2

    def point_from_start(self, distance: _decimal) -> _point.Point:
        line = Line(self._p1.copy(), None, distance, self.get_angle(self._p1))
        return line.p2

    @property
    def center(self) -> _point.Point:
        x = (self._p1.x + self._p2.x) * ZERO_5
        y = (self._p1.y + self._p2.y) * ZERO_5
        z = (self._p1.z + self._p2.z) * ZERO_5
        return _point.Point(x, y, z)

    def __iter__(self) -> _Iterable[_point.Point]:
        return iter([self._p1, self._p2])
