
from ... import utils as _utils
from ... import color as _color
from . import material as _material


class MetallicMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
    _shine = 51.2

    _cl_ambient = 0.0
    _cl_diffuse = 0.0
    _cl_specular = 0.0
    _cl_shininess = 51.2
    _cl_metallic = 0.8
    _cl_roughness = 0.5

    def __init__(self, color: _color.Color):
        r, g, b = color.rgb_scalar

        ar = _utils.remap(r, 0.75294, 1.0,
                          0.19215, 0.24705)
        ag = _utils.remap(g, 0.75294, 0.843137,
                          0.19215, 0.19607)
        ab = _utils.remap(b, 0.0, 0.75294,
                          0.07058, 0.19215)

        dr = _utils.remap(r, 0.75294, 1.0,
                          0.50588, 0.3451)
        dg = _utils.remap(g, 0.75294, 0.843137,
                          0.50588, 0.3137)
        db = _utils.remap(b, 0.0, 0.75294,
                          0.09019, 0.50588)

        sr = _utils.remap(r, 0.75294, 1.0,
                          0.50588, 0.79607)
        sg = _utils.remap(g, 0.75294, 0.843137,
                          0.50588, 0.72156)
        sb = _utils.remap(b, 0.0, 0.75294,
                          0.2078, 0.50588)

        self._ambient = (ar, ag, ab)
        self._diffuse = (dr, dg, db)
        self._specular = (sr, sg, sb)

        self._cl_specular = sum(self._specular) / len(self._specular)
        self._cl_diffuse = sum(self._diffuse) / len(self._diffuse)
        self._cl_ambient = sum(self._ambient) / len(self._ambient)

        super().__init__(color)
