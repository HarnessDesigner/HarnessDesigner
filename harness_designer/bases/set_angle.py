import math

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

    def set_x_angle(self, angle: _decimal, origin: "_point.Point") -> None:
        raise NotImplementedError

    def set_y_angle(self, angle: _decimal, origin: "_point.Point") -> None:
        raise NotImplementedError

    def set_z_angle(self, angle: _decimal, origin: "_point.Point") -> None:
        raise NotImplementedError

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "_point.Point"):
        raise NotImplementedError


from ..geometry import point as _point  # NOQA