import math

from ..wrappers.decimal import Decimal as _decimal


class GetAngleBase:

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self.get_x_angle(), self.get_y_angle(), self.get_z_angle()

    def get_x_angle(self) -> _decimal:
        raise NotImplementedError

    def get_y_angle(self) -> _decimal:
        raise NotImplementedError

    def get_z_angle(self) -> _decimal:
        raise NotImplementedError

    @staticmethod
    def _get_angle(coord1: tuple[_decimal, _decimal], coord2: tuple[_decimal, _decimal]) -> _decimal:
        p1, p2 = [_decimal(item) for item in coord1]
        p3, p4 = [_decimal(item) for item in coord2]

        r = math.atan2(p4 - p2, p3 - p1)
        angle = _decimal(math.degrees(float(r)))

        if angle < 0.0:
            angle += _decimal(360.0)

        return angle
