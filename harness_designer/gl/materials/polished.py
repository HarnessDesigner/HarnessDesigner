from ... import utils as _utils
from ... import color as _color
from . import material as _material


class PolishedMaterial(_material.GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
    _shine = 0.0

    def __init__(self, color: _color.Color):
        r, g, b = color.rgb_scalar

        ar = _utils.remap(r, 0.75294, 1.0,
                          0.22745, 0.24705)
        ag = _utils.remap(g, 0.75294, 0.843137,
                          0.22745, 0.22352)
        ab = _utils.remap(b, 0.0, 0.75294,
                          0.06274, 0.22745)

        dr = _utils.remap(r, 0.75294, 1.0,
                          0.27450, 0.34509)
        dg = _utils.remap(g, 0.75294, 0.843137,
                          0.27450, 0.31372)
        db = _utils.remap(b, 0.0, 0.75294,
                          0.09019, 0.27450)

        sr = _utils.remap(r, 0.75294, 1.0,
                          0.77254, 0.79607)
        sg = _utils.remap(g, 0.75294, 0.843137,
                          0.77254, 0.72156)
        sb = _utils.remap(b, 0.0, 0.75294,
                          0.20784, 0.77254)

        self._ambient = (ar, ag, ab)
        self._diffuse = (dr, dg, db)
        self._specular = (sr, sg, sb)

        self._shine = _utils.remap(r + g + b, 1.843137,
                                   2.25882, 83.2, 89.6)
        super().__init__(color)
