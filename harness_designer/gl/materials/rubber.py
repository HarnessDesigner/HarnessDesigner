
from ... import utils as _utils
from ... import color as _color
from . import material as _material


class RubberMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
    _shine = 10.0

    def __init__(self, color: _color.Color):

        r, g, b = color.rgb_scalar

        if r == g == b == 0.0:
            ar, ag, ab = (0.02, 0.02, 0.02)
            dr, dg, db = (0.01, 0.01, 0.01)
            sr, sg, sb = (0.4, 0.4, 0.4)
        else:
            ar = _utils.remap(r, 0.0, 1.0,
                              0.0, 0.05)
            ag = _utils.remap(g, 0.0, 1.0,
                              0.0, 0.05)
            ab = _utils.remap(b, 0.0, 1.0,
                              0.0, 0.05)

            dr = _utils.remap(r, 0.0, 1.0,
                              0.4, 0.5)
            dg = _utils.remap(g, 0.0, 1.0,
                              0.4, 0.5)
            db = _utils.remap(b, 0.0, 1.0,
                              0.4, 0.5)

            sr = _utils.remap(r, 0.0, 1.0,
                              0.04, 0.7)
            sg = _utils.remap(g, 0.0, 1.0,
                              0.04, 0.7)
            sb = _utils.remap(b, 0.0, 1.0,
                              0.04, 0.7)

        self._ambient = (ar, ag, ab)
        self._diffuse = (dr, dg, db)
        self._specular = (sr, sg, sb)
        super().__init__(color)
