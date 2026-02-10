from typing import TYPE_CHECKING

from . import base3d as _base3d
import numpy as np
from ..geometry import angle as _angle
from ..geometry import point as _point


if TYPE_CHECKING:
    from .. import Canvas as _Canvas
    from .. import gl_materials as _glm


class MeshGeneric(_base3d.Base3D):

    def __init__(self, canvas: "_Canvas", material: "_glm.GLMaterial",
                 selected_material: "_glm.GLMaterial", smooth: bool,
                 data: list[list[np.ndarray, np.ndarray]] | list[list[np.ndarray, np.ndarray, int]],
                 position: _point.Point | None = None,
                 angle: _angle.Angle | None = None):

        _base3d.Base3D.__init__(self, canvas, material, selected_material,
                                smooth, data, position, angle)
