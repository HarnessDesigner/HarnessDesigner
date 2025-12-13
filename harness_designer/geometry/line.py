from typing import Iterable as _Iterable
import math

import numpy as np

from . import point as _point
from ..wrappers.decimal import Decimal as _decimal
from .constants import ZERO_5
from . import angle as _angle


class Line:
    def __array_ufunc__(self, func, method, inputs, instance, **kwargs):
        if func == np.matmul:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr @= instance
                p1, p2 = arr.tolist()

                self._p1.x = _decimal(p1[0])
                self._p1.y = _decimal(p1[1])
                self._p1.z = _decimal(p1[1])

                self._p2.x = _decimal(p2[0])
                self._p2.y = _decimal(p2[1])
                self._p2.z = _decimal(p2[1])

                return self
            else:
                return inputs @ self.as_numpy

        if func == np.add:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr += instance
                p1, p2 = arr.tolist()

                self._p1.x = _decimal(p1[0])
                self._p1.y = _decimal(p1[1])
                self._p1.z = _decimal(p1[1])

                self._p2.x = _decimal(p2[0])
                self._p2.y = _decimal(p2[1])
                self._p2.z = _decimal(p2[1])
                return self
            else:
                return inputs + self.as_numpy

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr -= instance
                p1, p2 = arr.tolist()

                self._p1.x = _decimal(p1[0])
                self._p1.y = _decimal(p1[1])
                self._p1.z = _decimal(p1[1])

                self._p2.x = _decimal(p2[0])
                self._p2.y = _decimal(p2[1])
                self._p2.z = _decimal(p2[1])
                return self
            else:
                return inputs + self.as_numpy

        print('func:', func)
        print()
        print('method:', method)
        print()
        print('inputs:', inputs)
        print()
        print('instance:', instance)
        print()
        print('kwargs:', kwargs)
        print()

        raise RuntimeError

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

    @property
    def as_numpy(self) -> np.ndarray:
        p1 = self._p1.as_float
        p2 = self._p2.as_float

        return np.array([p1, p2], dtype=np.dtypes.Float64DType)

    @property
    def as_float(self) -> tuple[list[float, float, float], list[float, float, float]]:
        p1 = self._p1.as_float
        p2 = self._p2.as_float

        return p1, p2

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

    def get_rotated_line(self, angle: _decimal, pivot: _point.Point) -> "Line":
        """
        This is a 2d function and it only deals with the x and y axis.
        """

        if pivot is None:
            pivot = self.point_from_start(self.length() / _decimal(2.0))

        angle = _decimal(math.radians(angle))

        p1 = self._rotate_point(pivot, self._p1, angle)
        p2 = self._rotate_point(pivot, self._p2, angle)

        return Line(p1, p2)

    def get_parallel_line(self, offset: _decimal) -> "Line":
        """
        This is a 2d function and it only deals with the x and y axis.
        """

        offset /= _decimal(2.0)

        r = _decimal(math.radians(self.get_angle(self._p1).z + _decimal(90)))
        center = self.center
        x, y = center.x, center.y

        x += offset * _decimal(math.cos(r))
        y += offset * _decimal(math.sin(r))

        line = self.get_rotated_line(_decimal(180), _point.Point(x, y, _decimal(0.0)))
        line._p1, line._p2 = line._p2, line._p1

        return line

    @staticmethod
    def _rotate_point(origin: _point.Point, point: _point.Point, angle: _decimal) -> _point.Point:
        """
        This is a 2d function and it only deals with the x and y axis.
        """
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        cos = _decimal(math.cos(angle))
        sin = _decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return _point.Point(qx, qy)

