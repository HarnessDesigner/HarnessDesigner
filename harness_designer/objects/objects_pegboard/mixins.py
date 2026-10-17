# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board-editor specialization of the shared
``objects.mixins.wire.WireTypeMixin`` -- see that module's own module
docstring for the full rationale (shared ``_segments``/
``get_closest_point``/``get_closest_endpoint``, per-view
``_waypoints``/``_point_on_wire`` overrides).

The peg-board's own ``_point_on_wire`` is deliberately NOT the 3D
mixin's ray-cast (``Base3D``'s free-orbit camera makes a screen click
ambiguous in depth, so it has to intersect a ray against the wire's own
tube) -- the peg-board's camera is a locked top-down orthographic
projection, so ``camera.screen_to_world(mouse_pos)`` already gives an
unambiguous world X/Z position directly; the closest point is then just
plain 2D point-to-segment distance in that plane. Ported from
``drag_handlers.editor_pegboard.wire``'s own (now-shared)
``_closest_segment_index`` -- same math, moved here so it's reachable
through the object's own API instead of a free function private to
that module.
"""

from typing import TYPE_CHECKING, Union as _Union

import math

import numpy as np

from ...geometry import point as _point
from .. import mixins as _wire_type_base
from ...rope_pull import offline_store as _offline_store
from ... import check_types as _check_types
from ... import debug as _debug


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from ...database.project_db import pjt_point_pegboard as _pjt_point_pegboard
    from ...ui import editor_pegboard as _editor_pegboard


class WireTypeMixin(_wire_type_base.WireTypeMixin):
    """Peg-board chain-geometry helpers shared by ``Wire``/``Bundle`` --
    see the module docstring for the full rationale. A concrete class
    mixing this in must already provide ``start_position``/
    ``stop_position`` (live ``Point`` properties), ``db_obj`` (its own
    DB row, exposing ``waypoints_pegboard``), and ``pegboard`` (its own
    ``EditorPegboard``, for ``_point_on_wire``'s camera access).
    """
    pegboard: "_editor_pegboard.EditorPegboard" = None

    @staticmethod
    @_check_types.do
    def _waypoints(db_obj: _Union["_pjt_wire.PJTWire", "_pjt_bundle.PJTBundle"]) -> list["_pjt_point_pegboard.PJTPointPegboard"]:
        return db_obj.waypoints_pegboard

    @_check_types.do
    def _live_waypoint_points(self) -> list[_point.Point]:
        """The chain's interior waypoint Points in route order, as they are
        RIGHT NOW: the drag overlay (:mod:`rope_pull.offline_store`) while a
        drag has one open, else the saved path.

        A drag frame repositions the overlay and gives surplus waypoints up
        to a store without touching the saved path (only the release-time
        commit writes it), so the saved path is stale -- given-up points
        frozen where they were, newly created in-memory bends missing
        altogether -- for the whole drag. Drawing the strand from it made
        the wire show the previous shape until the mouse was released.
        """
        overlay_points = _offline_store.overlay_points(self.db_obj.db_id)
        if overlay_points is not None:
            return overlay_points

        return [waypoint.point for waypoint in self._waypoints(self.db_obj)]

    @_check_types.do
    def _live_waypoint_ids(self) -> list[bytes | None]:
        """Row ids matching :meth:`_live_waypoint_points` one for one --
        ``None`` for an in-memory bend a drag created that has no row yet.
        """
        entries = _offline_store.overlay(self.db_obj.db_id)
        if entries is not None:
            return [entry.point_id for entry in entries]

        return [waypoint.db_id for waypoint in self._waypoints(self.db_obj)]

    @_debug.logfunc
    @_check_types.do
    def _segments(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """Every (p1, p2) sub-segment from start, through each interior
        waypoint (:meth:`_live_waypoint_points`) in route order, to stop --
        the base implementation, but over the live overlay instead of the
        saved path.
        """
        points = [self.start_position.as_numpy]
        for point in self._live_waypoint_points():
            points.append(point.as_numpy)
        points.append(self.stop_position.as_numpy)

        return list(zip(points, points[1:]))

    @staticmethod
    @_check_types.do
    def _closest_point_on_segment_xz(seg_p1: np.ndarray, seg_p2: np.ndarray, click_x: float, click_z: float) -> tuple[float, float]:
        """Closest point on segment (seg_p1, seg_p2) -- X/Z plane only,
        Y ignored entirely (always 0.0 on the peg board) -- to
        (click_x, click_z), clamped to the segment itself.
        """
        ax, az = float(seg_p1[0]), float(seg_p1[2])
        bx, bz = float(seg_p2[0]), float(seg_p2[2])
        dx, dz = bx - ax, bz - az

        seg_len_sq = dx * dx + dz * dz
        if seg_len_sq < 1e-12:
            t = 0.0
        else:
            t = ((click_x - ax) * dx + (click_z - az) * dz) / seg_len_sq
            t = max(0.0, min(1.0, t))

        return ax + t * dx, az + t * dz

    @_check_types.do
    def _point_on_wire(
        self, mouse_pos: _point.Point
    ) -> tuple[np.ndarray, int] | tuple[None, None]:
        """Peg-board equivalent of the 3D mixin's own ``_point_on_wire``
        -- no ray to cast (the locked ortho camera already resolves
        *mouse_pos* to an unambiguous world X/Z position); whichever
        segment that position falls closest to (plain 2D distance)
        wins. Returns the winning segment's index, same meaning as the
        3D version's own (segment i sits between waypoint i-1 and
        waypoint i, see :meth:`_segments`).
        """
        segments = self._segments()
        if not segments:
            return None, None

        world_pos = self.pegboard.editor.camera.screen_to_world(mouse_pos)
        click_x, click_z = float(world_pos.x), float(world_pos.z)

        best_dist = math.inf
        best_point = None
        best_idx = None

        for i, (seg_p1, seg_p2) in enumerate(segments):
            px, pz = self._closest_point_on_segment_xz(seg_p1, seg_p2, click_x, click_z)
            dist = math.hypot(click_x - px, click_z - pz)

            if dist < best_dist:
                best_dist = dist
                best_point = np.array([px, 0.0, pz], dtype=np.float32)
                best_idx = i

        return best_point, best_idx
