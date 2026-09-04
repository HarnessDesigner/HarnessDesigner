# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ...objects.objects_3d import generic as _generic_3d
from ...objects.objects_schematic import generic as _generic_schematic
from ...objects.objects_pegboard import generic as _generic_pegboard
from ...objects import ObjectBase as _ObjectBase

from ...gl import materials as _materials
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import color as _color
from ... import config as _config
from ...shapes import sphere as _sphere
from ... import check_types as _check_types

if TYPE_CHECKING:
    from . import canvas as _canvas


Config = _config.Config.editor_3d


class FocalTarget(_ObjectBase):
    """Represent a focal point in :mod:`harness_designer.gl.canvas3d.focal_target`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`FocalPoint` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        # Subclasses _ObjectBase directly (not objects.generic.Generic --
        # that class's own __init__ unconditionally builds a placeholder
        # objects_3d.generic.Generic(self) with no vbo/angle/position/
        # scale/material, which that class requires with no defaults, so
        # it can never actually succeed as written). Same shape as
        # objects.housing.Housing: real mainframe + no db_obj, then this
        # class builds its own real objschematic/obj3d/objpegboard.
        super().__init__(canvas.mainframe, None)

        self.canvas = canvas
        self.objschematic = FocalTarget2D(self)
        self.obj3d = FocalTarget3D(self)
        self.objpegboard = FocalTargetPeg(self)


class FocalTargetPeg(_generic_pegboard.Generic):
    pass


class FocalTarget2D(_generic_schematic.Generic):
    pass


class FocalTarget3D(_generic_3d.Generic):
    """Represent a focal point 3D in :mod:`harness_designer.gl.canvas3d.focal_target`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: FocalTarget):
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

        super().__init__(parent, vbo, angle, position, scale, material)
