# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ...objects.objects3d import generic as _generic_3d
from ...objects.objects2d import generic as _generic_2d
from ...objects.objectspeg import generic as _generic_peg
from ...objects import generic as _generic

from ...gl import materials as _materials
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import color as _color
from ... import config as _config
from ...shapes import sphere as _sphere

if TYPE_CHECKING:
    from . import canvas as _canvas


Config = _config.Config.editor3d


class FocalPoint(_generic.Generic):
    """Represent a focal point in :mod:`harness_designer.gl.canvas3d.focal_target`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`FocalPoint` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        _generic.Generic.__init__(self, canvas)

        self.canvas = canvas
        self.obj2d = FocalPoint2D(self)
        self.obj3d = FocalPoint3D(self)
        self.objpeg = FocalPointPeg(self)


class FocalPointPeg(_generic_peg.Generic):
    pass


class FocalPoint2D(_generic_2d.Generic):
    pass


class FocalPoint3D(_generic_3d.Generic):
    """Represent a focal point 3D in :mod:`harness_designer.gl.canvas3d.focal_target`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "FocalPoint"):
        """Initialise the :class:`FocalPoint3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`FocalPoint`
        """
        self.canvas = parent.canvas

        color = _color.Color(*parent.canvas.config.focal_target.color)

        material = _materials.Metallic(color)
        angle = _angle.Angle()
        radius = Config.focal_target.radius

        scale = _point.Point(radius, radius, radius)
        position = parent.canvas.camera.focal_position
        vbo = _sphere.create_vbo()

        super().__init__(parent.canvas, vbo, angle, position, scale, material)

