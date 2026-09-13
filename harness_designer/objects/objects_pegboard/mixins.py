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

from typing import TYPE_CHECKING

import math

import numpy as np

from ...geometry import point as _point
from .. import mixins as _wire_type_base
from ... import check_types as _check_types


if TYPE_CHECKING:
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
    def _waypoints(db_obj):
        return getattr(db_obj, 'waypoints_pegboard', ())

    @staticmethod
    @_check_types.do
    def _closest_point_on_segment_xz(seg_p1, seg_p2, click_x: float, click_z: float):
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
