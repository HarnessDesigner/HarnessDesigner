import numpy as np

from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal
from ..wrappers import color as _color
from ..geometry.constants import ONE_65, NINE_0, ZERO_1666, ONEHUN_0

from . import hemisphere as _hemisphere


class Sphere(_hemisphere.Hemisphere):

    def __init__(self, center: _point.Point, diameter: _decimal,
                 color: _color.Color):

        super().__init__(center, diameter, color, None)
        self._sections = int((ONE_65 / (NINE_0 / (diameter ** ZERO_1666))) * ONEHUN_0) * 2

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._sections = int((ONE_65 / (NINE_0 / (value ** ZERO_1666))) * ONEHUN_0) * 2

        self._verts = None
        self._update_artist()

    def set_angles(self, x_angle: _decimal, y_angle: _decimal,
                   z_angle: _decimal, origin: _point.Point):

        if origin == self._center:
            return

        super().set_angles(x_angle, y_angle, z_angle, origin)

    @property
    def _line_space(self):
        return np.pi / 2
