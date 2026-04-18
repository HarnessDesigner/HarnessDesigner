from . import material as _material
from ... import color as _color


class GenericMaterial(_material.GLMaterial):
    _ambient = (0.3, 0.3, 0.3, 0.5)
    _diffuse = (0.5, 0.5, 0.5, 0.5)
    _specular = (0.8, 0.8, 0.8, 0.5)
    _shine = 50.0

    _cl_ambient = 0.0
    _cl_diffuse = 0.0
    _cl_specular = 0.0
    _cl_shininess = 50.0
    _cl_metallic = 0.0
    _cl_roughness = 0.5

    def __init__(self, color: _color.Color):
        scalar = color.rgb_scalar

        self._ambient = scalar
        self._diffuse = scalar
        self._specular = scalar

        self._cl_specular = sum(self._specular) / len(self._specular)
        self._cl_diffuse = sum(self._diffuse) / len(self._diffuse)
        self._cl_ambient = sum(self._ambient) / len(self._ambient)

        super().__init__(color)
