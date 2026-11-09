# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import math
from collections.abc import Iterator

import numpy as np
from PySide6 import QtWidgets
from PySide6 import QtCore

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...gl.canvas_base import interaction as _interaction
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from ... import utils as _utils
from . import mixins as _mixins
from ..mixins import tube as _tube
from ..mixins import waypoint_handles as _handles
from ... import check_types as _check_types
from ...crash_dump import Attr, capturable

if TYPE_CHECKING:
    from ...ui.editor_3d import editor_3d as _editor_3d
    from .. import ObjectBase as _ObjectBase
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire
    from ...gl import shaders as _shaders
    from ... import ui as _ui
    from .. import terminal as _terminal_facade
    from .. import splice as _splice_facade
    from . import bundle as _bundle_3d


Config = _config.Config.editor_3d

_CABLE_NOT_ATTACHED = ('A cable is not attached to a terminal or a splice itself: its conductors are, once the cable has '
                       'been split. Place the cable in free space.')


@capturable()
class Wire(_base_3d.Base3D, _mixins.WireTypeMixin, _tube.TubeMixin, _handles.WaypointOwnerMixin):
    """Represent a wire in :mod:`harness_designer.objects.objects_3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __dump_schema__ = (
        Attr('_part', severity=2),
        Attr('_p1', severity=2),
        Attr('_p2', severity=2),
        Attr('_length', severity=2),
        Attr('_bundle', severity=2),
        Attr('_stripe_material', severity=2),
    )

    parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire" = None

    # the end of a wire that crimps into a terminal is drawn as the bare conductor (objects/mixins/tube.py)
    _has_bare_ends = True

    # it casts the outline of its drawn path on the floor, not a rectangle per section
    _floor_projection_enabled = False

    @_check_types.do
    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        with parent.mainframe.editor3d.context:
            self._stripe_material = None

            # None for a wire that is not a twisted pair / triple, else a TwistLook
            self._twist = None
            self._init_tubes()

            self._part = db_obj.part
            color = self._part.color.ui
            stripe_color = self._part.stripe_color

            # across and through the cross-section: the same for a wire (a round tube at its od_mm); a cable view sizes a flat
            # ribbon differently
            width, thickness = self._trunk_size(self._part)
            diameter = width

            # Wires hold strong references to bundles as a sanity check
            self._bundle = None

            material = _materials.Plastic(color)

            # Bare-conductor look for whichever end segment(s) crimp into a
            # terminal (see render()) -- conductor_dia_mm already falls back
            # to an AWG-derived estimate when the wire_size_dia column is
            # NULL; od_mm * 2/3 is the final fallback for a part missing both,
            # per the same ratio a stranded conductor's copper core typically
            # is of its own fully-insulated OD.
            conductor_dia = self._part.conductor_dia_mm
            if not conductor_dia:
                conductor_dia = diameter * (2.0 / 3.0)

            self._conductor_dia = conductor_dia
            self._conductor_material = _materials.Polished(self._part.core_material.color.ui)

            self._twist = self._make_look(diameter)

            self._p1 = db_obj.start_position3d
            self._p2 = db_obj.stop_position3d

            # Live Point objects for every interior waypoint (idx order),
            # kept in sync with the DB via refresh_waypoints() -- called by
            # whichever handler adds/removes/reorders this wire's own
            # waypoints (handlers.wire_layout_handler, handlers.wire_handler,
            # objects.terminal.Terminal.add_wire).
            self._waypoint_points: list[_point.Point] = []

            # Raw point ids (see handlers.wire_topology.hidden_waypoint_ids)
            # that sit inside a bundle/transition this wire is routed
            # through -- recomputed only in _bind_waypoints (waypoint-
            # change time), never per frame, and read by
            # _segment_transforms to skip drawing that stretch
            # (BUNDLE_PLACEMENT.md section 12).
            self._hidden_waypoint_ids: set = set()

            self._length = self._calc_length()

            position = self._p1

            scale = _point.Point(width, thickness, self._length)

            # Track wires in this bundle using weak references
            # Wires hold strong references to bundles; bundles use weak refs to wires
            self._wires = []  # List of weak references to Wire objects

            self._p2.bind(self._update_position)

            vbo = _cylinder.create_vbo()
            angle = _angle.Angle()

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

            # the stripe is a material of the conductor, drawn by the tube mixin (objects/mixins/tube.py), not an object
            if stripe_color is not None:
                self._stripe_material = _materials.Plastic(stripe_color.ui)

            # _update_angle just calls _update_position(None) — redundant since
            # both endpoints already drive recalculation via their point bindings.
            self._angle.unbind(self._update_angle)

            # self.db_obj is only valid from here on (set by Base3D.__init__
            # above) -- this is the first point waypoints3d/for_wire can be
            # queried, so the initial waypoint bind and the real (possibly
            # multi-segment) geometry recompute both happen here, not earlier.
            self._bind_waypoints()
            self._recalculate_geometry()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wires

        return smooth

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @property
    @_check_types.do
    def length(self) -> float:
        return self._length

    @_check_types.do
    def _calc_length(self) -> float:
        """Straight-line seed length used only to size this wire's
        initial scale before Base3D.__init__ runs (self.db_obj isn't
        valid yet, so this can't query waypoints3d) -- a brand new wire
        row never has any waypoints yet anyway. _recalculate_geometry
        (called at the end of __init__, and on every subsequent endpoint/
        waypoint move) replaces this with the true, possibly multi-segment
        polyline length via WireTypeMixin._segments().
        """
        x1, y1, z1 = self._p1.as_numpy.tolist()
        x2, y2, z2 = self._p2.as_numpy.tolist()

        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @_check_types.do
    def _bind_waypoints(self) -> None:
        """(Re-)bind this wire's own _update_position callback to every
        current interior waypoint's live Point, unbinding it from whatever
        set was bound before.

        Called once at construction and again (as refresh_waypoints) by
        any handler that adds/removes/reorders this wire's own waypoints,
        so live position-change callbacks always match the current set.
        """
        for point in self._waypoint_points:
            point.unbind(self._update_position)

        # The rows are kept: a point writes its moves back to its row through a weak callback, so a move is saved only while
        # something holds the row. A waypoint that has a layout is held by it; a cable's has none, so this is what saves its moves.
        self._waypoint_rows = list(self.db_obj.waypoints3d)
        self._waypoint_points = [row.point for row in self._waypoint_rows]

        for point in self._waypoint_points:
            point.bind(self._update_position)

        from ...handlers import wire_topology as _wire_topology  # NOQA -- avoid a cycle at import time

        self._hidden_waypoint_ids = _wire_topology.hidden_waypoint_ids(
            self.mainframe.project.ptables, self.db_obj.db_id, '3d')

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Public entry point for handlers: call after this wire's own
        waypoint rows change (added, removed, or reordered) so live
        callbacks, cached length, and geometry all catch up."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.editor3d.Refresh()

        # The wire's own slack-handler safety net needs the same
        # refresh -- its own bound callbacks must match whatever is
        # actually in the route now, same reason _bind_waypoints()
        # itself just re-ran (see handlers.wire_slack_handler).
        self.parent._slack_handler.register_3d()  # NOQA

    @property
    @_check_types.do
    def start_position(self) -> _point.Point:
        """Wire start position (Point instance)"""
        return self._p1

    @property
    @_check_types.do
    def stop_position(self) -> _point.Point:
        """Wire stop position (Point instance)"""
        return self._p2

    @_check_types.do
    def is_housing_attached(self) -> bool:
        """True if either endpoint shares a db_id with any cavity's or
        terminal's housing-derived wire-routing point (cavity.wire_position3d,
        terminal.wire_position3d, terminal.attach_position3d) anywhere in
        the project. Such a wire's position is derived from its housing --
        it must not be independently draggable; the user has to move the
        housing or drag the wire's own layout instead.

        Checks the *_raw properties (no lazy point creation) so this never
        forces a wire-routing point into existence for a cavity/terminal
        that has never had one, just by asking.
        """
        start_id = self._p1.db_id[:-2]
        stop_id = self._p2.db_id[:-2]
        ids = {start_id, stop_id}

        project = self.mainframe.project

        for cavity in project.cavities:
            if cavity.db_obj.wire_position3d_id_raw in ids:
                return True

        for terminal in project.terminals:
            if terminal.db_obj.wire_position3d_id_raw in ids:
                return True
            if terminal.db_obj.attach_position3d_id_raw in ids:
                return True

        return False

    @_check_types.do
    def set_start_position(self, point: _point.Point) -> None:
        """Repoint this wire's own start end to *point* entirely.

        Not a merge/delegation (see Point.attach for that) -- the old
        start point is left alone as an independent point (e.g. becoming
        a permanent interior waypoint the instant before this is called;
        see handlers.wire_handler.AddWireHandler._commit_waypoint, the
        only caller today), and *point* must already be exactly where
        this wire's start should be -- nothing here moves it.
        """
        self._p1.unbind(self._update_position)
        self._p1 = point
        self._p1.bind(self._update_position)
        self._recalculate_geometry()

    @_check_types.do
    def set_stop_position(self, point: _point.Point) -> None:
        """See set_start_position."""
        self._p2.unbind(self._update_position)
        self._p2 = point
        self._p2.bind(self._update_position)
        self._recalculate_geometry()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle) -> None:
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._update_position(None)

    @staticmethod
    @_check_types.do
    def _trunk_size(part: object) -> tuple[float, float]:
        """How wide and how thick the tube is drawn, mm: round, at the part's ``od_mm``. A cable view overrides it (a ribbon is
        flat).

        :param part: The wire's catalog part.
        """
        return part.od_mm, part.od_mm

    @_check_types.do
    def reload_conductor_colors(self) -> None:
        """Draw a lead again in its conductor's colour and stripe colour after they were edited (a lead takes both from its
        conductor row through ``PJTWire.part``). A stripe that was added or removed needs the wire made again."""
        part = self.db_obj.part
        self._part = part
        self._material = _materials.Plastic(part.color.ui)
        self._gpu_look = None
        self._twist_plan = None

        stripe_color = part.stripe_color

        if self._stripe_material is not None and stripe_color is not None:
            self._stripe_material = _materials.Plastic(stripe_color.ui)

        self.editor3d.Refresh()

    @_check_types.do
    def _endpoint_diameter(self) -> float:
        return self.db_obj.part.od_mm

    @_check_types.do
    def _recalculate_geometry(self) -> None:
        """Compute total length, an aggregate angle, and OBB/AABB from
        the wire's current start/interior-waypoints/stop path.

        Per-segment position/angle/scale for actual drawing and hit-
        testing are computed fresh in render()/hit_test_step3 from
        WireTypeMixin._segments() -- this only maintains the aggregate
        values anything outside this class still reads (.length, .scale,
        .angle, .obb, .aabb).
        """
        self._twist_plan = None

        segments = self._segments()

        total_length = 0.0
        for seg_p1, seg_p2 in segments:
            total_length += float(np.linalg.norm(seg_p2 - seg_p1))

        if total_length < 0.001:
            return

        self._length = total_length
        self._scale.z = total_length

        # Aggregate angle: the overall start->stop chord direction. Not
        # used for drawing (each segment computes its own), kept only for
        # any other code reading .angle on a wire.
        a = self._p1.as_numpy
        b = self._p2.as_numpy
        chord = b - a
        chord_length = float(np.linalg.norm(chord))
        if chord_length >= 0.001:
            angle = self._rotation_from_direction(chord / chord_length)
            self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _update_position(self, _: _point.Point | None) -> None:
        """Recompute geometry immediately, not deferred to the next
        render pass -- bound to the start/stop endpoints and every
        interior waypoint (see _bind_waypoints), so any of them moving
        keeps the wire's aggregate length/OBB/AABB and the stripe's
        mesh capacity current before the next repaint.
        """
        self._recalculate_geometry()

    @_check_types.do
    def _segment_transforms(self) -> Iterator[tuple[_point.Point, _angle.Angle, _point.Point, float]]:
        """Yield (position, angle, scale, length) for every sub-segment
        of this wire's current path -- the values render()/hit_test_step3
        both draw/test against, computed fresh each call since a wire's
        waypoints can change at any time.

        Skips any sub-segment that lies entirely between two skeleton
        points (both its own endpoints in ``self._hidden_waypoint_ids``,
        cached by ``_bind_waypoints``) -- that stretch runs through a
        bundle's or transition's own rendered geometry, so drawing it
        again here would double it up (BUNDLE_PLACEMENT.md section 12).
        The guard waypoints bracketing that stretch are never themselves
        hidden, so the open-air stub segment on their outward side still
        renders normally.
        """
        width = self._scale.x
        thickness = self._scale.y
        hidden_ids = self._hidden_waypoint_ids

        point_ids = [self.start_position.db_id[:-2]]
        for wp in self._waypoints(self.db_obj):
            point_ids.append(wp.db_id)
        point_ids.append(self.stop_position.db_id[:-2])

        for (seg_p1, seg_p2), id1, id2 in zip(self._segments(), point_ids, point_ids[1:]):
            if hidden_ids and id1 in hidden_ids and id2 in hidden_ids:
                continue

            seg_vec = seg_p2 - seg_p1
            seg_len = float(np.linalg.norm(seg_vec))
            if seg_len < 1e-6:
                continue

            direction = seg_vec / seg_len
            seg_angle = self._rotation_from_direction(direction)
            seg_position = _point.Point(*seg_p1)
            seg_scale = _point.Point(width, thickness, seg_len)

            yield seg_position, seg_angle, seg_scale, seg_len

    @_check_types.do
    def _compute_obb(self) -> None:
        """Union AABB across every sub-segment, expressed as an 8-corner
        box (same shape find_object/_ray_intersect_obb expects) -- a
        single rigid OBB has no meaningful orientation for a wire with
        more than one bend, so this degenerates to the same envelope as
        _compute_aabb rather than a tight rotated box. Conservative (a
        click near an elbow but off the actual tube can still register a
        hit) but always correct; see hit_test_step3 for the precise,
        per-segment mesh test."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        mins = corners.min(axis=0)
        maxs = corners.max(axis=0)

        # Pool corner order (utils.bounding_boxes.compute_obb): 1 toggles x,
        # 3 toggles y, 4 toggles z -- see objects_schematic.wire.Wire.
        # _store_obb for what the AABB corner order did to picking.
        obb = np.array([
            [mins[0], mins[1], mins[2]], [maxs[0], mins[1], mins[2]],
            [maxs[0], maxs[1], mins[2]], [mins[0], maxs[1], mins[2]],
            [mins[0], mins[1], maxs[2]], [maxs[0], mins[1], maxs[2]],
            [maxs[0], maxs[1], maxs[2]], [mins[0], maxs[1], maxs[2]],
        ], dtype=np.float32)

        if self._obb is None:
            self._obb = self._obb_manager.read(self._obb_index)
            self._obb[:] = obb
        else:
            self._obb[:] = obb

    @_check_types.do
    def _compute_aabb(self) -> None:
        """See _compute_obb -- same union-of-segments envelope."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        aabb = _utils.adjust_aabb(corners)
        self._aabb[:] = aabb

    @_check_types.do
    def segment_obbs(self) -> np.ndarray:
        """(S, 8, 3) world-space oriented box of every sub-segment -- one per
        wire section, S being 0 when every section is degenerate.

        Corners are in the bounds pool's own OBB order (0 = min corner, 1
        toggles x, 3 toggles y, 4 toggles z, see _compute_obb), so anything
        built for a pool row works on one of these boxes unchanged. Unlike
        self.obb -- the union envelope of every section, which has no useful
        orientation once the wire bends -- each box is tight to its own
        section's cylinder; this is what a collision test against a wire
        needs (see objects_3d.wire_service_loop.WireServiceLoop).
        """
        local_min = self._vbo.local_aabb[0]
        local_max = self._vbo.local_aabb[1]
        x1, y1, z1 = local_min
        x2, y2, z2 = local_max

        local_corners = np.array([
            [x1, y1, z1], [x2, y1, z1], [x2, y2, z1], [x1, y2, z1],
            [x1, y1, z2], [x2, y1, z2], [x2, y2, z2], [x1, y2, z2]
        ], dtype=np.float32)

        boxes = []
        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            corners = local_corners * seg_scale.as_numpy
            corners = corners @ seg_angle
            corners = corners + seg_position.as_numpy
            boxes.append(corners)

        if not boxes:
            return np.empty((0, 8, 3), dtype=np.float32)

        return np.stack(boxes, axis=0)

    @_check_types.do
    def _segment_world_corners(self) -> np.ndarray:
        """World-space AABB corners (8 per segment) for every sub-segment,
        stacked into one array -- the shared building block for both
        _compute_obb and _compute_aabb's union-of-segments envelope."""
        boxes = self.segment_obbs()

        if not len(boxes):
            # Every sub-segment is degenerate (start and stop, and any
            # waypoints between them, all coincide) -- a real state a
            # wire can transiently be in (e.g. a wire service loop's own
            # placeholder "gap" wire, deleted a moment after construction
            # -- see handlers.wire_service_loop_handler._split_wire_for_
            # loop). A point-sized box at the wire's own position is
            # still a valid, if trivial, bound -- returning None left obb/
            # aabb permanently unset (None) instead.
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return boxes.reshape(-1, 3)

    @_check_types.do
    def hit_test_step3(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> bool:
        """Precise per-segment mesh hit test (see BaseVar.hit_test_step3):
        tests every sub-segment's own transformed triangles individually
        instead of assuming one rigid transform for the whole wire."""
        if self._vbo is None:
            return False

        vertices_local = self._vbo.vertices.reshape(-1, 3)
        if len(vertices_local) % 3:
            return False

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            ray_object = ray_origin - seg_position.as_numpy

            vertices = (vertices_local * seg_scale.as_numpy) @ seg_angle
            verts = vertices.reshape(-1, 3, 3)

            if self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts):
                return True

        return self._handle_hit(ray_origin, ray_dir)

    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the wire: hand it to the frame's batch (:meth:`_render_tubes`).

        Called once per wire per frame, so not wrapped in ``check_types.do``.
        """
        self._render_tubes()

    @_check_types.do
    def render_selected_overlay(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the wire's AABB/OBB/floor-projection overlays for every
        sub-segment of its current path, plus each waypoint layout
        marker's own overlays for completeness at a sharp bend (see
        ``_render_waypoint_layouts`` below) -- called directly by
        ``canvas_base.py::_render_selected_overlay`` once per frame, same
        as ``Base3D.render_selected_overlay`` itself (see that method's
        own docstring), just repeated per segment the same way ``render()``
        draws the wire's actual tube geometry once per segment. This is a
        separate loop over ``self._segment_transforms()`` from ``render()``'s
        own -- it runs later in the frame (after the floor, not as part
        of the normal per-object draw), so it can't just piggyback on
        that one.

        Temporarily points this object's position/angle/scale at each
        segment before delegating to ``Base3D.render_selected_overlay``
        -- the same swap-call-restore idiom ``render()``'s own per-segment
        loop already uses (``self._vbo`` doesn't need swapping here since
        every segment shares the wire's own single cylinder mesh).
        """
        if not self.is_selected:
            return

        real_position, real_angle, real_scale = (
            self._position, self._angle, self._scale)

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            self._position, self._angle, self._scale = seg_position, seg_angle, seg_scale
            super().render_selected_overlay(shaders)

        self._position, self._angle, self._scale = (
            real_position, real_angle, real_scale)

        self._render_waypoint_layouts(shaders)
        self._render_floor_outline(shaders)

    @_check_types.do
    def _render_waypoint_layouts(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw each waypoint layout marker's own AABB/OBB/floor-projection
        overlays for completeness -- a bent wire's per-segment overlays
        (drawn once per segment by ``render_selected_overlay`` above)
        don't cover the joint at a sharp bend by themselves; the small
        sphere ``WireLayout`` marker sitting at each waypoint fills that
        gap. These draw because the WIRE is selected, not because any
        individual ``WireLayout`` is -- called once here, not once per
        segment, and never through ``Base3D.render_selected_overlay``
        (which is tied to this object's own ``is_visible``/selected
        state, not a waypoint's).

        Temporarily swaps ``self._vbo``/``self._position``/``self._angle``/
        ``self._scale`` to each waypoint's own sphere/position/identity/
        diameter and calls ``_render_overlay_group`` -- the same
        AABB/OBB/floor-projection group draw ``render_selected_overlay``
        itself uses per segment (see that method's own docstring for why
        the group is drawn together rather than as 3 separate calls), and
        the identical swap-call-restore idiom this method's own caller
        already uses per segment, just with a sphere instead of a
        cylinder segment.
        """
        if not self._waypoint_points:
            return

        real_vbo, real_position, real_angle, real_scale = (
            self._vbo, self._position, self._angle, self._scale)

        diameter = (self._part.od_mm if self._part is not None else 3.0) * _handles.HANDLE_SCALE

        self._vbo = _sphere.create_vbo()
        self._angle = _angle.Angle()
        self._scale = _point.Point(diameter, diameter, diameter)

        for point in self._waypoint_points:
            self._position = point
            self._render_overlay_group(shaders)

        self._vbo, self._position, self._angle, self._scale = (
            real_vbo, real_position, real_angle, real_scale)

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        super().set_selected(flag)

    @staticmethod
    @_check_types.do
    def _rotation_from_direction(direction: np.ndarray) -> _angle.Angle:
        """Create quaternion to rotate +Z axis to align with direction"""
        # Unit cylinder points along +Z, rotate it to point along 'direction'
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Handle special case: direction already aligned with Z (tight
        # epsilon -- this only exists to dodge the near-zero-length cross
        # product below, not to treat "close to vertical" as "vertical")
        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 1e-6:
            return _angle.Angle.from_quat([1.0, 0.0, 0.0, 0.0])  # Identity

        if abs(dot + 1.0) < 1e-6:
            # 180 degree rotation around X axis
            return _angle.Angle.from_quat([0.0, 1.0, 0.0, 0.0])

        # Calculate rotation axis and angle
        axis = np.cross(z_axis, direction)  # NOQA
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return _angle.Angle.from_axis_angle(axis, angle)

    @property
    @_check_types.do
    def bundle(self) -> _Union["_bundle_3d.Bundle", None]:
        """Return the bundle this wire belongs to, if any."""
        return self._bundle

    @bundle.setter
    @_check_types.do
    def bundle(self, value: _Union["_bundle_3d.Bundle", None]) -> None:
        """Set the bundle this wire belongs to.

        Wires hold strong references to bundles as a sanity check.
        """
        self._bundle = value

    @property
    @_check_types.do
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    @_check_types.do
    def is_visible(self, value: bool) -> None:
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value
        self.db_obj.is_visible = value

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", terminal: _Union["_terminal_facade.Terminal", None] = None,
        splice: _Union["_splice_facade.Splice", None] = None,
        extend_wire: tuple | None = None, add_to_wire: tuple | None = None,
        preset_part_id: bytes | None = None, mouse_pos: _point.Point | None = None
    ) -> _Union["_wire.Wire", None]:
        """Entry point for every way a 3D wire-placement session can
        start -- toolbar mode-select (all args None: free-space) or a
        context-menu action (exactly one of the others). Resolves the
        part (and, for a terminal/splice start, checks compatibility) up
        front, builds the real facade object (or grabs the existing wire
        being extended/continued -- see add_handlers.editor_3d.wire.Wire's
        own module docstring for why those two never create a fresh
        preview), arms its add-session, and arms the canvas's own
        active_handler_obj pointer -- so callers just need this return
        value to know whether anything actually started (None means the
        part-search dialog was cancelled, or an incompatible-part
        confirmation was declined).

        :param preset_part_id: Skip GetSelection()/the part-search dialog
            entirely and start a free-space placement with this part --
            "Add Wire" from an existing wire's own context menu (same
            part, no re-pick).
        """
        canvas = mainframe.editor3d.editor

        if preset_part_id is not None:
            return cls._start_free_space(mainframe, canvas, preset_part_id)

        from ...handlers import wire_handler as _wire_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db

        if terminal is not None:
            initial_params = _wire_handler.terminal_wire_search_params(terminal)
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.WiresPage, mainframe.global_db.wires_table, 'Add Wire',
                initial_params=initial_params)

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

            return cls._start_from_terminal(mainframe, canvas, terminal, part_id)

        if splice is not None:
            initial_params = _wire_handler.splice_wire_search_params(splice)
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.WiresPage, mainframe.global_db.wires_table, 'Add Wire',
                initial_params=initial_params)

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

            return cls._start_from_splice(mainframe, canvas, splice, part_id)

        if extend_wire is not None:
            wire_obj, end_point = extend_wire
            return cls._start_extend_from_wire(mainframe, canvas, wire_obj, end_point)

        if add_to_wire is not None:
            wire_obj, end_point = add_to_wire
            return cls._start_add_to_wire(mainframe, canvas, wire_obj, end_point)

        part_id = mainframe.editor_db.editor.wires.GetSelection()
        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.WiresPage, mainframe.global_db.wires_table, 'Add Wire')

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        facade = cls._start_free_space(mainframe, canvas, part_id)

        # Free-space start only: *mouse_pos* (the empty-space context menu's
        # own click) is where the wire's first point is dropped; the session
        # is then left armed for its second click as usual.
        if facade is not None and mouse_pos is not None:
            from ...add_handlers import base as _add_base

            _add_base.click_at(canvas, facade.obj3d, mouse_pos)

        return facade

    @classmethod
    @_check_types.do
    def _start_from_terminal(
            cls, mainframe: "_ui.MainFrame", canvas: "_editor_3d.Editor3DPanel", terminal: "_terminal_facade.Terminal",
            part_id: bytes) -> _Union["_wire.Wire", None]:
        """Pin the preview wire's start to *terminal* and enter phase 1
        directly -- see handlers.wire_handler.AddWireHandler.
        _start_from_terminal, the original of this method.
        """
        from ...handlers import wire_snap as _wire_snap
        from .. import wire as _wire_facade

        ptables = mainframe.project.ptables
        wire_part = mainframe.global_db.wires_table[part_id]

        if wire_part.is_cable:
            QtWidgets.QMessageBox.information(mainframe, 'Cable', _CABLE_NOT_ATTACHED)
            return None

        ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(terminal, wire_part)
        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QtWidgets.QMessageBox.question(mainframe, 'Incompatible Wire', block_msg)
            if button == QtWidgets.QMessageBox.StandardButton.No:
                return None

        start_circuit_id = terminal.db_obj.circuit_id

        placeholder_id = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

        initial_pos = terminal.db_obj.attach_position3d
        stop_db = ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        name = f'{wire_part.manufacturer.name} {wire_part.part_number}'

        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, start_circuit_id,
            placeholder_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)

        terminal.add_wire(facade, 'start')
        ptables.pjt_points3d_table[placeholder_id].delete()

        return cls._arm(canvas, facade, part_id, phase=1, growing_point=facade.obj3d.stop_position,
                        start_circuit_id=start_circuit_id)

    @classmethod
    @_check_types.do
    def _start_from_splice(
            cls, mainframe: "_ui.MainFrame", canvas: "_editor_3d.Editor3DPanel", splice: "_splice_facade.Splice",
            part_id: bytes) -> _Union["_wire.Wire", None]:
        from ...handlers import wire_snap as _wire_snap
        from .. import wire as _wire_facade

        ptables = mainframe.project.ptables
        wire_part = mainframe.global_db.wires_table[part_id]

        if wire_part.is_cable:
            QtWidgets.QMessageBox.information(mainframe, 'Cable', _CABLE_NOT_ATTACHED)
            return None

        ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(splice, wire_part)
        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QtWidgets.QMessageBox.question(mainframe, 'Incompatible Wire', block_msg)
            if button == QtWidgets.QMessageBox.StandardButton.No:
                return None

        start_point_id = splice.db_obj.branch_position3d_id
        initial_pos = splice.obj3d.wire_position

        stop_db = ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        name = f'{wire_part.manufacturer.name} {wire_part.part_number}'

        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, None,
            start_point_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)

        splice.add_wire(facade)
        facade.set_sibling(splice, facade.obj3d.start_position)

        return cls._arm(
            canvas, facade, part_id, phase=1, growing_point=facade.obj3d.stop_position,
            start_circuit_id=None)

    @classmethod
    @_check_types.do
    def _start_extend_from_wire(
            cls, mainframe: "_ui.MainFrame", canvas: "_editor_3d.Editor3DPanel", wire_obj: "_wire.Wire",
            end_point: _point.Point) -> _Union["_wire.Wire", None]:
        """Extension mode: live-move *wire_obj*'s own dangling end
        (identified by *end_point*, the actual ``Point`` the caller
        picked -- not a 'start'/'stop' label) directly, never creating a
        fresh preview -- see add_handlers.editor_3d.wire.Wire's own
        module docstring.
        """
        obj3d = wire_obj.obj3d
        start_np = obj3d.start_position.as_numpy
        stop_np = obj3d.stop_position.as_numpy
        is_start = end_point is obj3d.start_position

        if is_start:
            endpoint_np = start_np
            seg = start_np - stop_np
        else:
            endpoint_np = stop_np
            seg = stop_np - start_np

        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-8:
            return None

        from ...add_handlers.editor_3d import wire as _add_wire

        handler = _add_wire.Wire(
            canvas, wire_obj, wire_obj.db_obj.part_id, phase=1,
            start_circuit_id=wire_obj.db_obj.circuit_id,
            extension_mode=True, source_wire=wire_obj, source_point=end_point)

        handler._extension_dir = seg / seg_len  # NOQA
        handler._extension_origin = endpoint_np.copy()  # NOQA
        handler._extension_original_pos = endpoint_np.copy()  # NOQA

        wire_obj.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = wire_obj.obj3d

        return wire_obj

    @classmethod
    @_check_types.do
    def _start_add_to_wire(
            cls, mainframe: "_ui.MainFrame", canvas: "_editor_3d.Editor3DPanel", wire_obj: "_wire.Wire",
            end_point: _point.Point) -> _Union["_wire.Wire", None]:
        """Continue *wire_obj* from its own free end (identified by
        *end_point*, not a 'start'/'stop' label) -- tags that end as a
        permanent interior waypoint, then continues the live preview
        from a fresh point there. Unlike every other entry point,
        *wire_obj* is a real, already-placed, already-registered wire
        the whole time (see add_handlers.editor_3d.wire.Wire's own
        ``_preexisting_wire``/``_growing_point`` handling).
        """
        from ...add_handlers.editor_3d import wire as _add_wire

        handler = _add_wire.Wire(
            canvas, wire_obj, wire_obj.db_obj.part_id, phase=1, growing_point=end_point,
            preexisting_wire=True, start_circuit_id=wire_obj.db_obj.circuit_id)

        wire_obj.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = wire_obj.obj3d

        handler._commit_growing_point_as_waypoint()  # NOQA

        return wire_obj

    @classmethod
    @_check_types.do
    def _start_free_space(cls, mainframe: "_ui.MainFrame", canvas: "_editor_3d.Editor3DPanel", part_id: bytes) -> _Union["_wire.Wire", None]:
        """Build the preview wire eagerly, at a placeholder start point
        the hover calls relocate to the cursor -- see the module-level
        docstring on add_handlers.editor_3d.wire.Wire. The wire is HIDDEN
        until the first click has set its start (the placeholder stop
        point still sits at the origin through all of phase 0, so showing
        it would draw a wire from the origin to the cursor); the session
        shows it once the end being placed follows the cursor.
        """
        from .. import wire as _wire_facade

        ptables = mainframe.project.ptables
        wire_part = mainframe.global_db.wires_table[part_id]

        # A shielded wire, or one with more than one conductor, is placed as a cable (TWISTED_WIRE_DESIGN.md, section 8a)
        if wire_part.is_cable:
            from . import cable as _cable_3d  # NOQA -- avoid a cycle at import time

            return _cable_3d.Cable.start_add_cable(mainframe, canvas, part_id)

        start_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        stop_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        name = f'{wire_part.manufacturer.name} {wire_part.part_number}'

        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, None,
            start_db.db_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)
        facade.obj3d.is_visible = False

        return cls._arm(
            canvas, facade, part_id, phase=0, growing_point=facade.obj3d.start_position,
            start_circuit_id=None)

    @classmethod
    @_check_types.do
    def _arm(cls, canvas: "_editor_3d.Editor3DPanel", facade: "_wire.Wire", part_id: bytes, phase: int,
             growing_point: _point.Point, start_circuit_id: bytes | None) -> "_wire.Wire":
        from ...add_handlers.editor_3d import wire as _add_wire

        handler = _add_wire.Wire(
            canvas, facade, part_id, phase=phase, growing_point=growing_point,
            start_circuit_id=start_circuit_id)

        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def get_context_menu(self) -> "WireMenu":
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireMenu(self.mainframe.editor3d.editor, self)

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Segment-local wire drag -- overrides Base3D's generic single-
        position drag outright: what a click on the wire's body actually
        moves (a free end, a waypoint pair, or nothing draggable at all)
        is computed by drag_handlers.editor_3d.wire.plan_wire_drag; see
        that module's own docstring for the full rule. A snap committed
        mid-drag (drag_handlers.editor_3d.wire.Wire.snapped_kind/
        snapped_target) is only made real here, on release -- mirroring
        exactly what the two-click placement flow's own inline commits do
        (see handlers.wire_snap.commit_snap's own docstring).

        Also forwards to an active add-session (see
        add_handlers.editor_3d.wire.Wire) OR an active wire-routing
        click-continuation (handlers.wire_routing_drag.RouteSession,
        BUNDLE_PLACEMENT.md section 12 -- the click-driven "pick which
        branch to exit a transition from" step once a routing drag has
        landed mid-skeleton) -- all three of this object's own
        interaction modes (bend/route drag, wire-placement session,
        routing click-continuation) share the one self._active_handler
        slot (never simultaneously), told apart by which kind is
        actually armed since their call shapes differ (an add/
        continuation session takes the full event tuple this method
        itself received; a drag takes just a screen delta + position).
        """
        from ...add_handlers.editor_3d import wire as _add_wire  # NOQA -- avoid a cycle at import time
        from ...handlers import wire_routing_drag as _wire_routing_drag  # NOQA -- avoid a cycle at import time

        if self._waypoint_drag:
            return self._handle_waypoint_drag(last_pos, current_pos, interaction_type)

        if isinstance(self._active_handler, (_add_wire.Wire, _wire_routing_drag.RouteSession)):
            # A local reference, not another read of self._active_handler below
            # -- a right click with nothing left to undo cancels the session,
            # which deletes this wire's own facade; BaseVar's generic delete()
            # sees self._active_handler is this same handler and clears it AND
            # calls its own delete() (idempotent -- cancel() already ran) right
            # there, all before this call even returns. Reading self.
            # _active_handler again afterward would find None -- checked
            # AttributeError, confirmed live 2026-09-21 (Kevin) -- ask the
            # handler itself, and only clear the slot if nothing already did.
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        if self._active_handler is not None:
            from ...drag_handlers.editor_3d import wire_route as _wire_route  # NOQA -- avoid a cycle at import time

            if interaction_type is _interaction.MouseInteraction.MOVE:
                self._active_handler(current_pos - last_pos, current_pos)
                return True

            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                handler = self._active_handler

                if isinstance(handler, _wire_route.WireRoute) and handler.drop_hit is not None:
                    # Dropped on an eligible bundle end/transition branch
                    # (BUNDLE_PLACEMENT.md section 12) -- route instead of
                    # just leaving the ordinary bend in place. anchor is
                    # the path point nearest the original click, moved
                    # rigidly with the dragged pair all drag long -- still
                    # resolves to the originally-grabbed section (see
                    # handlers.wire_routing_handler.route_wire's own
                    # docstring on what grabbed_position needs to be).
                    hit = handler.drop_hit
                    grabbed_position = handler.anchor.as_numpy
                    canvas = handler.canvas
                    handler.delete()
                    self._active_handler = None

                    session = _wire_routing_drag.begin_route(
                        canvas, self.parent, grabbed_position, hit, '3d')
                    if session is not None:
                        self._active_handler = session

                    return True

                try:
                    if handler.snap_point is not None and handler.snapped_kind is not None:
                        from ...handlers import wire_snap as _wire_snap  # NOQA -- avoid a cycle at import time
                        # commit_snap's own `end` parameter stays a string --
                        # reconstruct it here, once, right at this boundary.
                        end = 'start' if handler.snap_point is self.start_position else 'stop'
                        _wire_snap.commit_snap(
                            self.mainframe, self.parent, end,
                            handler.snapped_kind, handler.snapped_target)
                finally:
                    # a commit that raises must not leave the drag armed (its gesture open, and the next release committing again)
                    handler.delete()
                    self._active_handler = None

                # No real drag happened -- let a plain click-release fall
                # through to the default select/deselect toggle instead of
                # being eaten here (see objects_3d.base_3d.handle_interaction).
                return had_motion

            return False

        if (
            interaction_type is not _interaction.MouseInteraction.LEFT_DOWN or
            clicked_object is not self.parent or
            self.parent.mainframe.get_selected() is not self.parent
        ):
            return False

        # a press on one of this object's waypoint handles drags that waypoint (objects/mixins/waypoint_handles.py)
        if self._arm_waypoint_drag(current_pos):
            return True

        from ...drag_handlers.editor_3d import wire_route as _wire_route  # NOQA -- avoid a cycle at import time

        plan = _wire_route.WireRoute.plan_wire_drag(self.mainframe.project, self.parent, current_pos)
        if plan is None:
            return False

        self._active_handler = _wire_route.WireRoute(self.editor3d.editor, self.parent, plan)
        return True


class WireMenu(QtWidgets.QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects_3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_editor_3d.Editor3DPanel", selected: Wire):
        """Initialise the :class:`WireMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Layout')
        action.triggered.connect(self.on_add_handle)

        action = self.addAction('Delete Layout')
        action.setEnabled(bool(selected._waypoint_points))  # NOQA
        action.setToolTip('Remove the waypoint nearest the right click')
        action.triggered.connect(self.on_delete_layout)

        action = self.addAction('Add Marker')
        action.triggered.connect(self.on_add_marker)

        action = self.addAction('Add Splice')
        action.triggered.connect(self.on_add_splice)

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        self.addSeparator()

        from ...drag_handlers.editor_3d import wire as _wire_3d  # NOQA -- avoid a cycle at import time

        wire = selected.parent
        click_pos = selected._context_menu_click_pos  # NOQA
        free_end = _wire_3d.Wire.pick_free_end(selected.mainframe, wire, click_pos)

        action = self.addAction('Extend Wire')
        action.setEnabled(free_end is not None)
        action.triggered.connect(self.on_extend_wire)

        action = self.addAction('Add to Wire')
        action.setEnabled(free_end is not None)
        action.triggered.connect(self.on_add_to_wire)

        can_add_terminal = False
        if free_end is wire.obj3d.start_position:
            can_add_terminal = wire.start_sibling is None
        elif free_end is wire.obj3d.stop_position:
            can_add_terminal = wire.stop_sibling is None

        action = self.addAction('Add Terminal')
        action.setEnabled(can_add_terminal)
        action.triggered.connect(self.on_add_terminal)

        self.addSeparator()
        action = self.addAction('Add to Bundle')
        action.triggered.connect(self.on_add_to_bundle)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

        # A lead of a cable's conductor is a wire with its own route: Add Layout, Extend Wire, Add Terminal, Add to Wire, Add Splice and
        # Add Wire Service Loop work as on any wire (a splice or a loop splits it in two, and both halves stay that conductor's wire,
        # see handlers.wire_topology.split_wire_at_point). Only 'Add Wire' makes no sense: it would place a new, free wire of the
        # CABLE's part, which is not a conductor.
        if wire.db_obj.is_cable_lead:
            for action in self.actions():
                if action.text() in self._NOT_ON_A_LEAD:
                    action.setEnabled(False)
                    action.setToolTip('Not available on the lead of a cable conductor')

    _NOT_ON_A_LEAD = ('Add Wire',)

    @_check_types.do
    def _midpoint(self) -> _point.Point:
        """Return the world space midpoint of the wire."""
        line = _line.Line(self.selected.start_position,
                          self.selected.stop_position)

        return line.point_from_start(line.length() / 2.0)

    @_check_types.do
    def on_add_handle(self) -> None:
        """Start the interactive waypoint-placement flow (see
        add_handlers.editor_3d.wire_layout), seeded at the point on the
        wire that was right-clicked to open this menu (falls back to the
        wire's own midpoint if no click point was captured -- e.g. the
        menu was opened some other way). A live preview follows the
        cursor from there (snapping onto the wire's own true start/stop
        when close enough) until the next click commits it.
        """
        from . import wire_layout as _wire_layout_3d

        mainframe = self.selected.mainframe
        wire = self.selected.parent

        click_pos = self.selected._context_menu_click_pos  # NOQA
        initial_pos = None
        if click_pos is not None:
            initial_pos, _angle, _insert_idx = self.selected.get_closest_point(click_pos)

        if initial_pos is None:
            # No click captured -- fall back to the wire's own midpoint.
            initial_pos = self._midpoint()

        @_check_types.do
        def _do() -> None:
            _wire_layout_3d.WireLayout.start_add(mainframe, wire, initial_pos)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_delete_layout(self) -> None:
        """Remove the waypoint nearest the right click that opened this menu."""
        self.selected.delete_closest_waypoint(self.selected._context_menu_click_pos)  # NOQA

    @_check_types.do
    def on_add_marker(self) -> None:
        """Add a wire marker at the point on the wire that was
        right-clicked to open this menu (falls back to the wire's
        midpoint if no click point was captured -- e.g. the menu was
        opened some other way)."""
        @_check_types.do
        def _do() -> None:
            from .. import wire_marker as _wire_marker_obj

            mainframe = self.selected.mainframe

            part_id = _menu_ops.get_part_id(
                mainframe, mainframe.editor_db.editor.wire_markers,
                mainframe.global_db.wire_markers_table, 'Add Wire Marker')

            if part_id is None:
                return

            click_pos = self.selected._context_menu_click_pos  # NOQA
            position = None
            if click_pos is not None:
                position, _angle, _idx = self.selected.get_closest_point(click_pos)

            if position is None:
                position = self._midpoint()

            ptables = mainframe.project.ptables
            p3d = ptables.pjt_points3d_table.insert(*position.as_float)

            db_obj = ptables.pjt_wire_markers_table.insert(
                None, p3d.db_id, self.selected.db_obj.db_id, part_id, '')

            marker = _wire_marker_obj.WireMarker(mainframe, db_obj)
            mainframe.project.add_wire_marker(marker)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_splice(self) -> None:
        """Start the interactive splice placement flow on this wire."""
        from . import splice as _splice_3d

        mainframe = self.selected.mainframe
        wire = self.selected.parent

        # Deferred past the menu closing since it may open a modal
        # part-search dialog, same reasoning menu_ops.start_handler exists
        # for.
        @_check_types.do
        def _do() -> None:
            _splice_3d.Splice.start_add(mainframe, wire=wire)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_wire(self) -> None:
        """Start placing another wire of the same part type."""
        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        @_check_types.do
        def _do() -> None:
            Wire.start_add(mainframe, preset_part_id=part_id)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_extend_wire(self) -> None:
        """Grow this wire's free end in its current direction, with no
        waypoint/layout added -- see Wire.start_add's own
        extend_wire branch / add_handlers.editor_3d.wire's module
        docstring."""
        from ...drag_handlers.editor_3d import wire as _wire_3d  # NOQA -- avoid a cycle at import time

        mainframe = self.selected.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        end_point = _wire_3d.Wire.pick_free_end(mainframe, wire, click_pos)
        if end_point is None:
            return

        @_check_types.do
        def _do() -> None:
            Wire.start_add(mainframe, extend_wire=(wire, end_point))

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_terminal(self) -> None:
        """Crimp a new terminal (not in a cavity) onto this wire's free
        end -- see objects_3d.terminal.Terminal.add_at_wire_end."""
        from ...drag_handlers.editor_3d import wire as _wire_3d  # NOQA -- avoid a cycle at import time
        from . import terminal as _terminal_3d

        mainframe = self.selected.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        end_point = _wire_3d.Wire.pick_free_end(mainframe, wire, click_pos)
        if end_point is None:
            return

        @_check_types.do
        def _do() -> None:
            _terminal_3d.Terminal.add_at_wire_end(mainframe, wire, end_point)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_to_wire(self) -> None:
        """Drop a waypoint + layout at this wire's free end and continue
        it from there, freely -- see Wire.start_add's own add_to_wire
        branch / add_handlers.editor_3d.wire's module docstring."""
        from ...drag_handlers.editor_3d import wire as _wire_3d  # NOQA -- avoid a cycle at import time

        mainframe = self.selected.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        end_point = _wire_3d.Wire.pick_free_end(mainframe, wire, click_pos)
        if end_point is None:
            return

        @_check_types.do
        def _do() -> None:
            Wire.start_add(mainframe, add_to_wire=(wire, end_point))

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_wire_service_loop(self) -> None:
        """Start placing a service loop on this wire, anchored at the point
        that was right-clicked to open this menu."""
        from . import wire_service_loop as _wire_service_loop_3d

        mainframe = self.selected.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        @_check_types.do
        def _do() -> None:
            _wire_service_loop_3d.WireServiceLoop.start_add(mainframe, wire, click_pos)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_to_bundle(self) -> None:
        """Add this wire to the closest bundle in the project."""
        mainframe = self.selected.mainframe
        midpoint = self._midpoint()

        closest = None
        closest_distance = None

        for bundle in mainframe.project.bundles:
            b_line = _line.Line(bundle.obj3d.start_position,
                                bundle.obj3d.stop_position)
            b_mid = b_line.point_from_start(b_line.length() / 2.0)

            distance = _line.Line(midpoint, b_mid).length()

            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest = bundle

        if closest is None:
            return

        closest.obj3d.add_wire(self.selected)
        self.selected.bundle = closest.obj3d

        mainframe.editor3d.Refresh()

    @_check_types.do
    def on_trace_circuit(self) -> None:
        """Highlight every object on this wire's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self) -> None:
        """Make this wire the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_delete(self) -> None:
        """Delete this wire from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self) -> None:
        """Show this wire's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
