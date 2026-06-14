# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

# from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...gl import vbo as _vbo
from ...gl import materials as _materials


if TYPE_CHECKING:
    from .. import generic as _generic


class Generic(_base3d.Base3D):
    """Represent a generic in :mod:`harness_designer.objects.objects3d.generic`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_generic.Generic" = None

    def __init__(self, parent: "_generic.Generic", vbo: _vbo.PooledVBOHandler | None,
                 angle: _angle.Angle, position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial):

        parent.mainframe.editor3d.context.acquire()
        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, scale, material)
        parent.mainframe.editor3d.context.release()

