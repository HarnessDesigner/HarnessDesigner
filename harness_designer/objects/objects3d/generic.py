from typing import TYPE_CHECKING

import numpy as np

# from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...gl import vbo as _vbo
from ...gl import materials as _materials


if TYPE_CHECKING:
    from .. import generic as _generic


class Generic(_base3d.Base3D):
    parent: "_generic.Generic" = None

    def __init__(self, parent: "_generic.Generic", vbo: _vbo.VBOHandler | None,
                 angle: _angle.Angle, position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial, data=list[np.ndarray, np.ndarray, int] | None):

        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, scale, material, data)
