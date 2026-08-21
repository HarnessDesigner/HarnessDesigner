# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import numpy as np

from . import base_pegboard as _base_pegboard
from . import chain_edges as _chain_edges
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ...shapes import cylinder as _cylinder
from ... import utils as _utils
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


Config = _config.Config.editor_pegboard


class Wire(_base_pegboard.BasePegboard):
    """Peg-board representation of a wire -- a chain of straight cylinder
    segments from its start point, through every interior waypoint
    (:attr:`db_obj.waypoints_pegboard`, idx order), to its stop point.
    Mirrors :class:`objects_pegboard.bundle.Bundle` almost exactly (same
    multi-segment render trick, same union-of-segments OBB/AABB, same
    full-span-for-now scope -- see that class's own docstring on the
    deferred "leader" feature, which applies here identically), adapted
    for a wire's own catalog diameter/color (``db_obj.part.od_mm``/
    ``color``, mirroring ``objects_3d.wire.Wire.__init__``'s own
    ``Plastic`` material choice) instead of a bundle's concentric-layer
    diameter. No stripe overlay or bare-conductor crimp-end treatment
    (``objects_3d.wire.Wire``'s own ``WireStripe``/``_conductor_segment_
    ends``) -- those are 3D-only cosmetic refinements, not needed for the
    peg board's own schematic-style view.

    Like ``Bundle``, has no independent anchor presence of its own on the
    board (no single ``point3d_id``) -- it's a chain, not a point.
    """
    db_obj: "_pjt_wire.PJTWire"

    @_check_types.do
    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        self.db_obj = db_obj

        # scale/material built fresh from the catalog part's own data,
        # mirroring objects_3d.wire.Wire.__init__'s own construction --
        # never borrowed from obj3d (see base_pegboard.BasePegboard.
        # __init__'s own docstring on why).
        self._part = db_obj.part
        self._diameter = self._part.od_mm

        material = _materials.Plastic(self._part.color.ui)

        self._p1 = db_obj.start_position_pegboard
        self._p2 = db_obj.stop_position_pegboard

        # Live Point objects for every interior waypoint (idx order),
        # kept in sync with the DB via refresh_waypoints() -- same
        # pattern as objects_3d.wire.Wire's own _waypoint_points, called
        # by whichever handler adds/removes/reorders this wire's own
        # peg-board waypoints.
        self._waypoint_points: list[_point.Point] = []

        position = self._p1
        angle = _angle.Angle()
        scale = _point.Point(self._diameter, self._diameter, 0.0)

        with parent.mainframe.editor_pegboard.context:
            vbo = _cylinder.create_vbo()

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self._p2.bind(self._update_position)

        # self.db_obj is only valid from here on (set by BaseVar.__init__
        # above, via super().__init__()) -- this is the first point
        # waypoints_pegboard can be queried, so the initial waypoint bind
        # and the real (possibly multi-segment) geometry recompute both
        # happen here, not earlier -- mirrors objects_3d.wire.Wire's own
        # construction order exactly.
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
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @property
    @_check_types.do
    def diameter(self) -> float:
        return self._diameter

    @_check_types.do
    def _bind_waypoints(self) -> None:
        """(Re-)bind this wire's own _update_position callback to every
        current interior waypoint's live Point, unbinding it from
        whatever set was bound before -- mirrors
        objects_3d.wire.Wire._bind_waypoints exactly.
        """
        for point in self._waypoint_points:
            point.unbind(self._update_position)

        self._waypoint_points = [wp.point for wp in self.db_obj.waypoints_pegboard]

        for point in self._waypoint_points:
            point.bind(self._update_position)

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Public entry point for handlers: call after this wire's own
        peg-board waypoint rows change (added, removed, or reordered) so
        live callbacks and cached geometry all catch up.
        """
        self._bind_waypoints()
        self._recalculate_geometry()
        self.pegboard.Refresh()

    @_check_types.do
    def set_start_position(self, point: _point.Point) -> None:
        """Repoint this wire's own start end to *point* entirely -- see
        objects_3d.wire.Wire.set_start_position (same reasoning).
        """
        self._p1.unbind(self._update_position)
        self._p1 = point
        self._p1.bind(self._update_position)
        self._recalculate_geometry()

    @_check_types.do
    def set_stop_position(self, point: _point.Point) -> None:
        """See :meth:`set_start_position`."""
        self._p2.unbind(self._update_position)
        self._p2 = point
        self._p2.bind(self._update_position)
        self._recalculate_geometry()

    @_check_types.do
    def _update_scale(self, scale: _point.Point):
        # Length (scale.z) is a derived aggregate recomputed by
        # _recalculate_geometry, never written directly -- mirrors
        # objects_pegboard.bundle.Bundle's own no-op override.
        pass

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        # This object's own self._angle is just an aggregate chord
        # direction -- render()/OBB/AABB all derive their real
        # per-segment transforms from position, not this value. Mirrors
        # objects_pegboard.bundle.Bundle's own override.
        self._update_position(None)

    @_check_types.do
    def _segments(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """Every (p1, p2) sub-segment from start, through each interior
        waypoint in idx order, to stop -- as numpy arrays. A wire with no
        interior waypoints is just the one (start, stop) pair.
        """
        points = [self._p1.as_numpy]
        for point in self._waypoint_points:
            points.append(point.as_numpy)
        points.append(self._p2.as_numpy)

        return list(zip(points, points[1:]))

    @staticmethod
    @_check_types.do
    def _rotation_from_direction(direction) -> "_angle.Angle":
        """Rotate the unit cylinder's local +Z axis to point along
        *direction* -- mirrors objects_3d.wire.Wire._rotation_from_
        direction exactly (same math, same reasoning); duplicated
        locally rather than shared since that method lives on
        objects_3d.mixins.WireTypeMixin, which otherwise pulls in
        3D-only mouse-ray/hit-test machinery this class has no use for.
        """
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 1e-6:
            return _angle.Angle.from_quat([1.0, 0.0, 0.0, 0.0])
        if abs(dot + 1.0) < 1e-6:
            return _angle.Angle.from_quat([0.0, 1.0, 0.0, 0.0])

        axis = np.cross(z_axis, direction)  # NOQA
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return _angle.Angle.from_axis_angle(axis, angle)

    @_check_types.do
    def _segment_transforms(self):
        """Yield (position, angle, scale, length) for every sub-segment
        of this wire's current path -- mirrors objects_3d.wire.Wire._
        segment_transforms exactly.
        """
        diameter = self._scale.x

        for seg_p1, seg_p2 in self._segments():
            seg_vec = seg_p2 - seg_p1
            seg_len = float(np.linalg.norm(seg_vec))
            if seg_len < 1e-6:
                continue

            direction = seg_vec / seg_len
            seg_angle = self._rotation_from_direction(direction)
            seg_position = _point.Point(*seg_p1)
            seg_scale = _point.Point(diameter, diameter, seg_len)

            yield seg_position, seg_angle, seg_scale, seg_len

    @_check_types.do
    def _recalculate_geometry(self):
        """Compute total length and OBB/AABB from the wire's current
        start/interior-waypoints/stop path -- mirrors
        objects_pegboard.bundle.Bundle._recalculate_geometry exactly.
        """
        segments = self._segments()

        total_length = 0.0
        for seg_p1, seg_p2 in segments:
            total_length += float(np.linalg.norm(seg_p2 - seg_p1))

        if total_length < 0.001:
            total_length = 0.001

        self._scale.z = total_length

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _update_position(self, _: "_point.Point | None"):
        """Recompute geometry immediately, not deferred to the next
        render pass -- bound to the start/stop endpoints and every
        interior waypoint (see :meth:`_bind_waypoints`).
        """
        self._recalculate_geometry()

    @_check_types.do
    def _compute_obb(self):
        """Union AABB across every sub-segment, expressed as an 8-corner
        box -- mirrors objects_pegboard.bundle.Bundle._compute_obb
        exactly (same reasoning: a single rigid OBB has no meaningful
        orientation for a wire with more than one bend).
        """
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        mins = corners.min(axis=0)
        maxs = corners.max(axis=0)

        self._obb = np.array([
            [mins[0], mins[1], mins[2]], [mins[0], mins[1], maxs[2]],
            [mins[0], maxs[1], mins[2]], [mins[0], maxs[1], maxs[2]],
            [maxs[0], mins[1], mins[2]], [maxs[0], mins[1], maxs[2]],
            [maxs[0], maxs[1], mins[2]], [maxs[0], maxs[1], maxs[2]],
        ], dtype=np.float32)

    @_check_types.do
    def _compute_aabb(self):
        """See :meth:`_compute_obb` -- same union-of-segments envelope."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    @_check_types.do
    def _segment_world_corners(self):
        """World-space AABB corners (8 per segment) for every
        sub-segment, stacked into one array -- mirrors
        objects_pegboard.bundle.Bundle._segment_world_corners exactly.
        """
        local_min = self._vbo.local_aabb[0]
        local_max = self._vbo.local_aabb[1]
        x1, y1, z1 = local_min
        x2, y2, z2 = local_max

        local_corners = np.array([
            [x1, y1, z1], [x1, y1, z2],
            [x1, y2, z1], [x1, y2, z2],
            [x2, y1, z1], [x2, y1, z2],
            [x2, y2, z1], [x2, y2, z2]
        ], dtype=np.float32)

        all_corners = []
        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            corners = local_corners * seg_scale.as_numpy
            corners = corners @ seg_angle
            corners = corners + seg_position.as_numpy
            all_corners.append(corners)

        if not all_corners:
            # Every sub-segment is degenerate (start and stop, and any
            # waypoints between them, all coincide) -- a point-sized box
            # at the wire's own position is still a valid, if trivial,
            # bound.
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return np.concatenate(all_corners, axis=0)

    @_check_types.do
    def render(self, faces_program, edges_program, vertices_program):
        """Render every sub-segment of the wire's current path.

        Geometry is always current by the time this runs --
        _update_position recomputes it synchronously the moment any
        endpoint or waypoint moves. Each sub-segment is drawn as its own
        straight cylinder by temporarily pointing this object's own
        position/angle/scale at that segment before delegating to the
        inherited BaseVar.render() -- mirrors
        objects_pegboard.bundle.Bundle.render() exactly.
        """
        real_position, real_angle, real_scale = self._position, self._angle, self._scale

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            self._position, self._angle, self._scale = seg_position, seg_angle, seg_scale
            super().render(faces_program, edges_program, vertices_program)

        self._position, self._angle, self._scale = real_position, real_angle, real_scale

    @_check_types.do
    def touching_edges(self, point_pegboard_id: bytes) -> list:
        """Return this wire's chain edges touching *point_pegboard_id* --
        see ``chain_edges.touching_edges``.
        """
        return _chain_edges.touching_edges(self.db_obj, point_pegboard_id)

    @property
    @_check_types.do
    def start_position(self) -> _point.Point:
        """Wire start position (Point instance)."""
        return self._p1

    @property
    @_check_types.do
    def stop_position(self) -> _point.Point:
        """Wire stop position (Point instance)."""
        return self._p2
