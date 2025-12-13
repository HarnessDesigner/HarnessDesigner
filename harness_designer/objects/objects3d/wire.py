from typing import TYPE_CHECKING

import python_utils
import build123d

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ...database.project_db import pjt_wire as _pjt_wire
    
    
def build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal, has_stripe: bool):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / _decimal(2.0)

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    if has_stripe:
        # Extract the axis of rotation from the wire to create the stripe
        wire_axis = model.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

        # the stripe is actually a separate 3D object and it carries with it a thickness.
        # The the stripe is not thick enough the wire color will show through it. We don't
        # want to use a hard coded thickness because the threshold for for this happpening
        # causes the stripe thickness to increaseto keep the "bleed through" from happening.
        # A remap of the diameter to a thickness range is done to get a thickness where the
        # bleed through will not occur while keeping the stripe from looking like it is not
        # apart of the wire.
        stripe_thickness = python_utils.remap(diameter, old_min=_decimal(0.5), old_max=_decimal(5.0),
                                              new_min=_decimal(0.005), new_max=_decimal(0.015))

        edges = model.edges().filter_by(build123d.GeomType.CIRCLE)
        edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
        edges = edges.trim_to_length(0, float(diameter / _decimal(3.0) * _decimal(build123d.MM)))

        stripe_arc = build123d.Face(edges.offset_2d(float(stripe_thickness * _decimal(build123d.MM)), side=build123d.Side.RIGHT))

        # Define the twist path to follow the wire
        twist = build123d.Helix(
            pitch=float(wire_length / _decimal(2.0)),
            height=float(wire_length),
            radius=float(wire_radius),
            center=wire_axis.position,
            direction=wire_axis.direction,
        )

        # Sweep the arc to create the stripe
        stripe = build123d.sweep(
            stripe_arc,
            build123d.Line(wire_axis.position, float(wire_length * _decimal(wire_axis.direction))),
            binormal=twist
        )
    else:
        stripe = None

    bb = model.bounding_box()

    corner1 = _point.Point(*[_decimal(item) for item in bb.min])
    corner2 = _point.Point(*[_decimal(item) for item in bb.max])

    return model, stripe, (corner1, corner2)


class Wire(_Base3D):

    def __init__(self, editor3d: "_Editor3D", wire_db: "_pjt_wire.PJTWire"):
        super().__init__(editor3d)
        self._db_obj = wire_db
        self._part = wire_db.part

        self._p1 = wire_db.start_point3d.point
        self._p2 = wire_db.stop_point3d.point
        self._is_visible = self._db_obj.is_visible

        self._dia = self._part.od_mm

        self._model = None
        self._stripe = None
        self._hit_test_rect = None

        self._triangles = []
        self._stripe_triangles = []

        self._p1.Bind(self.recalculate)
        self._p2.Bind(self.recalculate)

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._is_visible = value
        self._db_obj.is_visible = value

        if not value:
            self._model = None
            self._stripe = None
            self._hit_test_rect = None
            self._triangles = None
            self._stripe_triangles = None
            self._normals = None
            self._stripe_normals = None
            self._triangle_count = 0
            self._stripe_triangle_count = 0

    def recalculate(self, *_):
        if self._is_visible:
            (
                self._model,
                self._stripe,
                self._hit_test_rect
            ) = build_model(self._p1, self._p2, self._part.od_mm,
                            self._part.stripe_color is not None)

            angle = _angle.Angle(self._p1, self._p2)
            p1, p2 = self._hit_test_rect
            p2 @= angle

            p1 += self._p1
            p2 += self._p1

            self._triangles = [self.editor3d.renderer.build_mesh(self._model)]
            if self._stripe is not None:
                self._stripe_triangles = [self.editor3d.renderer.build_mesh(self._stripe)]
        else:
            self._model = None
            self._stripe = None
            self._hit_test_rect = None

    def hit_test(self, point: _point.Point) -> bool:
        if self._hit_test_rect is None:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if not self._is_visible:
            return

        if self._is_visible and self._model is None:
            self.recalculate()

        if self._triangles is None:
            self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)

            if self._stripe is not None:
                self._stripe_normals, self._stripe_triangles, self._stripe_triangle_count = self._get_triangles(self._stripe)

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count, self._ui_primary_color.rgb_scalar)

        if self._stripe is not None:
            renderer.draw_triangles(self._stripe_normals, self._stripe_triangles, self._stripe_triangle_count, self._ui_stripe_color.rgb_scalar)
