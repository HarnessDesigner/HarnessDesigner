from . import material as _material


class GlowingMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.55, 0.55, 0.55)
    _specular = (0.70, 0.70, 0.70)
    _shine = 92.0

    def __init__(self, color):
        self._emissive = color.rgba_scalar
        self.diffuse = color.rgb_scalar

        _material.GLMaterial.__init__(self, color)
