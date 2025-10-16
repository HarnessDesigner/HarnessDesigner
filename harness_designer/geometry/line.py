from typing import Iterable as _Iterable
import numpy as np
import math

from .. import bases
from . import point as _point
from ..wrappers.decimal import Decimal as _decimal


class Line(bases.SetAngleBase, bases.GetAngleBase):

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

            x_angle = np.radians(x_angle)
            y_angle = np.radians(y_angle)
            z_angle = np.radians(z_angle)

            Rx = np.array([[1, 0, 0],
                          [0, np.cos(float(x_angle)), -np.sin(float(x_angle))],
                          [0, np.sin(float(x_angle)), np.cos(float(x_angle))]])

            Ry = np.array([[np.cos(float(y_angle)), 0, np.sin(float(y_angle))],
                          [0, 1, 0],
                          [-np.sin(float(y_angle)), 0, np.cos(float(y_angle))]])

            Rz = np.array([[np.cos(float(z_angle)), -np.sin(float(z_angle)), 0],
                          [np.sin(float(z_angle)), np.cos(float(z_angle)), 0],
                          [0, 0, 1]])

            R = Rz @ Ry @ Rx
            v = np.array([float(length), 0, 0])

            xyz = R @ v + np.array((float(p1.x), float(p1.y), float(p1.z)))

            p2 = _point.Point(_decimal(xyz[0]), _decimal(xyz[1]), _decimal(xyz[2]))

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
        return self.p2

    def __len__(self) -> int:
        res = math.sqrt((self._p2.x - self._p1.x) ** _decimal('2') +
                        (self._p2.y - self._p1.y) ** _decimal('2') +
                        (self._p2.z - self._p1.z) ** _decimal('2'))

        return int(round(res))

    def length(self) -> _decimal:
        return math.sqrt((self._p2.x - self._p1.x) ** _decimal(2) +
                         (self._p2.y - self._p1.y) ** _decimal(2) +
                         (self._p2.z - self._p1.z) ** _decimal(2))

    def get_x_angle(self) -> _decimal:
        return self._get_angle((self._p1.z, self._p1.y), (self._p2.z, self._p2.y))

    def get_y_angle(self) -> _decimal:
        return self._get_angle((self._p1.x, self._p1.z), (self._p2.x, self._p2.z))

    def get_z_angle(self) -> _decimal:
        return self._get_angle((self._p1.x, self._p1.y), (self._p2.x, self._p2.y))

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal,
                   origin: _point.Point | None = None) -> None:

        if origin is None:
            origin = self.center

        with self._p1 and self._p2:
            self.set_x_angle(x_angle, origin)
            self.set_y_angle(y_angle, origin)
            self.set_z_angle(z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: _point.Point | None = None) -> None:
        if origin is None:
            origin = self.center

        if origin == self._p1:
            self._p2.z, self._p2.y = self._rotate_point((self._p2.z, self._p2.y), angle, (origin.z, origin.y))
        elif origin == self._p2:
            self._p1.z, self._p1.y = self._rotate_point((self._p1.z, self._p1.y), angle, (origin.z, origin.y))
        else:
            self._p2.z, self._p2.y = self._rotate_point((self._p2.z, self._p2.y), angle, (origin.z, origin.y))
            self._p1.z, self._p1.y = self._rotate_point((self._p1.z, self._p1.y), angle, (origin.z, origin.y))

    def set_y_angle(self, angle: _decimal, origin: _point.Point | None = None) -> None:
        if origin is None:
            origin = self.center

        if origin == self._p1:
            self._p2.x, self._p2.z = self._rotate_point((self._p2.x, self._p2.z), angle, (origin.x, origin.z))
        elif origin == self._p2:
            self._p1.x, self._p1.z = self._rotate_point((self._p1.x, self._p1.z), angle, (origin.x, origin.z))
        else:
            self._p2.x, self._p2.z = self._rotate_point((self._p2.x, self._p2.z), angle, (origin.x, origin.z))
            self._p1.x, self._p1.z = self._rotate_point((self._p1.x, self._p1.z), angle, (origin.x, origin.z))

    def set_z_angle(self, angle: _decimal, origin: _point.Point | None = None) -> None:
        if origin is None:
            origin = self.center

        if origin == self._p1:
            self._p2.x, self._p2.y = self._rotate_point((self._p2.x, self._p2.y), angle, (origin.x, origin.y))
        elif origin == self._p2:
            self._p1.x, self._p1.y = self._rotate_point((self._p1.x, self._p1.y), angle, (origin.x, origin.y))
        else:
            self._p2.x, self._p2.y = self._rotate_point((self._p2.x, self._p2.y), angle, (origin.x, origin.y))
            self._p1.x, self._p1.y = self._rotate_point((self._p1.x, self._p1.y), angle, (origin.x, origin.y))

    @property
    def center(self) -> _point.Point:
        return _point.Point(
            self._p1.x + (self._p1.x - self._p2.x),
            self._p1.y + (self._p1.y - self._p2.y),
            self._p1.z + (self._p1.z - self._p2.z)
        )

    def __iter__(self) -> _Iterable[_point.Point]:
        yield self._p1
        yield self._p2
