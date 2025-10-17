import math
import numpy as np
from ..wrappers.decimal import Decimal as _decimal


class SetAngleBase:

    @staticmethod
    def _rotate_point(point: tuple[_decimal, _decimal],
                      angle: int | float,
                      origin: tuple[_decimal, _decimal]) -> tuple[_decimal, _decimal]:

        angle = math.radians(angle)

        ox, oy = [_decimal(item) for item in origin]
        px, py = [_decimal(item) for item in point]

        cos = _decimal(math.cos(angle))
        sin = _decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return qx, qy

    @staticmethod
    def _get_rotation_matrix(angle_x: _decimal, angle_y: _decimal,
                             angle_z: _decimal) -> np.array:

        x_angle = np.radians(float(angle_x))
        y_angle = np.radians(float(angle_y))
        z_angle = np.radians(float(angle_z))

        Rx = np.array([[1, 0, 0],
                       [0, np.cos(x_angle), -np.sin(x_angle)],
                       [0, np.sin(x_angle), np.cos(x_angle)]])

        Ry = np.array([[np.cos(y_angle), 0, np.sin(y_angle)],
                       [0, 1, 0],
                       [-np.sin(y_angle), 0, np.cos(y_angle)]])

        Rz = np.array([[np.cos(z_angle), -np.sin(z_angle), 0],
                       [np.sin(z_angle), np.cos(z_angle), 0],
                       [0, 0, 1]])

        return Rz @ Ry @ Rx

    def set_x_angle(self, angle: _decimal, origin: "_point.Point") -> None:
        raise NotImplementedError

    def set_y_angle(self, angle: _decimal, origin: "_point.Point") -> None:
        raise NotImplementedError

    def set_z_angle(self, angle: _decimal, origin: "_point.Point") -> None:
        raise NotImplementedError

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "_point.Point"):
        raise NotImplementedError


from ..geometry import point as _point  # NOQA