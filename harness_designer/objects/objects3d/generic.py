# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
    """Represent a generic in :mod:`harness_designer.objects.objects3d.generic`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_generic.Generic" = None

    def __init__(self, parent: "_generic.Generic", vbo: _vbo.VBOHandler | None,
                 angle: _angle.Angle, position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial, data=list[np.ndarray, np.ndarray, np.ndarray, int] | None):
        """Initialise the :class:`Generic` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_generic.Generic`
        :param vbo: Value for ``vbo``.
        :type vbo: _vbo.VBOHandler | None
        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        :param position: Position value.
        :type position: :class:`_point.Point`
        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        :param material: Value for ``material``.
        :type material: :class:`_materials.GLMaterial`
        :param data: Data payload.
        :type data: UNKNOWN
        """

        parent.mainframe.editor3d.context.acquire()
        if vbo is not None:
            vbo.acquire()
        
        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, scale, material, data)
        parent.mainframe.editor3d.context.release()

