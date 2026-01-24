from typing import TYPE_CHECKING

import python_utils
import build123d

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from ... import gl_materials as _gl_materials

from ... import Config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire
    

Config = Config.editor3d


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal, has_stripe: bool):
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
            build123d.Line(wire_axis.position, float(wire_length) * wire_axis.direction),
            binormal=twist
        )
    else:
        stripe = None

    return model, stripe


class Wire(_base3d.Base3D):
    _parent: "_wire.Wire" = None

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        _base3d.Base3D.__init__(self, parent)
        self._db_obj: "_pjt_wire.PJTWire" = db_obj

        self._part = db_obj.part

        self._color = self._part.color.ui
        self._stripe_color = self._part.stripe_color
        self._diameter: _decimal = None
        self._is_dragging = False
        self._is_visible = db_obj.is_visible

        # Wires hold strong references to bundles as a sanity check
        self._bundle = None

        self._diameter = self._part.od_mm

        self._model = None
        self._stripe = None

        if self._stripe_color is None:
            self._stripe_material = None
        else:
            self._stripe_material = _gl_materials.Plastic(self._stripe_color.ui.rgba_scalar)

        self._material = _gl_materials.Plastic(self._color.rgba_scalar)

        start_layout = db_obj.start_layout
        stop_layout = db_obj.stop_layout

        self._is_start_clickable = start_layout is None
        self._is_stop_clickable = stop_layout is None

        self._p1 = db_obj.start_point3d.point
        self._p2 = db_obj.stop_point3d.point

        # Track wires in this bundle using weak references
        # Wires hold strong references to bundles; bundles use weak refs to wires
        self._wires = []  # List of weak references to Wire objects

        self._p1.bind(self._build)
        self._p2.bind(self._build)

        self._build()

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value: bool):
        if value != self._is_dragging:
            self._is_dragging = value

            if value:
                # this is the agnostic for a bundle. Instead of rendering the bundle
                # over and over again which can get a bit expensive the larger the diameter
                # of the bundle instead we swap out the rendering of the cylinder
                # for rendering a line that is the same color.
                # it's not going to look as pretty but it will be a lot faster to render.

                # TODO: set dragging mode for wires if the end of the bundle is being dragged.

                self._triangles = _base3d.LineRenderer(
                    self._p1, self._p2, self._diameter,
                    self._color.rgba_scalar
                    )
            else:
                self._build()
        else:
            self._is_dragging = value

    def _build(self, _=None):
        if self._is_dragging:
            return

        wire_model, stripe_model = _build_model(self._p1, self._p2, self._diameter, self._stripe_color is not None)

        vertices, faces = self._convert_model_to_mesh(wire_model)

        tris, nrmls, count = self._get_triangles(vertices, faces)
        angle = _angle.Angle.from_points(self._p1, self._p2)

        tris @= angle
        nrmls @= angle
        tris += self._p1

        p1, p2 = self._compute_rect(tris)

        self._position = ((p2 - p1) / _decimal(2.0)) + p1

        self._bb = [self._compute_bb(p1, p2)]
        self._rect = [[p1, p2]]

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

        if stripe_model is not None:
            vertices, faces = self._convert_model_to_mesh(wire_model)

            tris, nrmls, count = self._get_triangles(vertices, faces)

            self._triangles.append(_base3d.TriangleRenderer([[tris, nrmls, count]], self._stripe_material))

        for item in self._triangles:
            item.is_visible = self.is_visible

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_wires:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    @property
    def bundle(self):
        """Return the bundle this wire belongs to, if any."""
        return self._bundle
    
    @bundle.setter
    def bundle(self, value):
        """Set the bundle this wire belongs to.
        
        Wires hold strong references to bundles as a sanity check.
        """
        self._bundle = value

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._is_visible = value
        self._db_obj.is_visible = value

        for item in self._triangles:
            item.is_visible = value
