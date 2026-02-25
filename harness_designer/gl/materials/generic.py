from . import material as _material
from ... import color as _color


class GenericMaterial(_material.GLMaterial):
    _ambient = (0.3, 0.3, 0.3, 0.5)
    _diffuse = (0.5, 0.5, 0.5, 0.5)
    _specular = (0.8, 0.8, 0.8, 0.5)
    _shine = 50.0

    def __init__(self, color: _color.Color):
        scalar = color.rgb_scalar

        self._ambient = scalar
        self._diffuse = scalar
        self._specular = scalar
        super().__init__(color)
