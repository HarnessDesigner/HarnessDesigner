from . import material as _material
from ... import color as _color


class PlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.898039, 0.898039, 0.898039)
    _shine = 110.0

    _cl_ambient = 0.0
    _cl_diffuse = 0.0
    _cl_specular = 0.898039
    _cl_shininess = 110.0
    _cl_metallic = 0.0
    _cl_roughness = 0.1

    def __init__(self, color: _color.Color):
        scalar = color.rgb_scalar

        self._ambient = scalar
        self._diffuse = scalar

        self._cl_diffuse = sum(self._diffuse) / len(self._diffuse)
        self._cl_ambient = sum(self._ambient) / len(self._ambient)

        super().__init__(color)


class BlackPlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.01, 0.01, 0.01)
    _specular = (0.50, 0.50, 0.50)
    _shine = 32.0


class CyanPlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.1, 0.06)
    _diffuse = (0.0, 0.50980392, 0.50980392)
    _specular = (0.50196078, 0.50196078, 0.50196078)
    _shine = 32.0


class GreenPlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.1, 0.35, 0.1)
    _specular = (0.45, 0.55, 0.45)
    _shine = 32.0


class RedPlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.5, 0.0, 0.0)
    _specular = (0.7, 0.6, 0.6)
    _shine = 32.0


class WhitePlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.55, 0.55, 0.55)
    _specular = (0.70, 0.70, 0.70)
    _shine = 32.0


class YellowPlasticMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.5, 0.5, 0.0)
    _specular = (0.60, 0.60, 0.50)
    _shine = 32.0
