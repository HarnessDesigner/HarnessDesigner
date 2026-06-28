# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for inserting wire service loops.

Single-click workflow: hovering over any wire shows a preview helix-loop
sized from the wire's outer diameter.  A click finalises placement — the
wire is split at the two connection points and a service loop object is
inserted between them.

Intersection avoidance: up to 16 candidate orientations (22.5° increments
rotating around the wire axis) are tested; the first orientation whose
bounding volume does not overlap nearby wires or existing loops is used.
"""

import math
import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_service_loop as _wire_service_loop
from ..objects import wire as _wire
from ..shapes import cylinder_helix as _cylinder_helix
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _quat_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product of two [w, x, y, z] quaternions."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ], dtype=np.float64)


def _compute_stop(
    start_pos: _point.Point,
    wire_angle: "_angle.Angle",
    diameter: float,
) -> _point.Point:
    """Return the world-space exit point of the helix.

    Mirrors exactly what WireServiceLoop 3D __init__ does when position2 is
    at the origin: scale the VBO endpoint by diameter, rotate by wire_angle,
    translate to start_pos.
    """
    vbo = _cylinder_helix.create_vbo()
    scale = _point.Point(diameter, diameter, diameter)
    stop_local = vbo.endpoint.copy()
    stop_local *= scale
    stop_local @= wire_angle
    stop_local += start_pos
    return stop_local


def _seg_closest_dist_sq(
    p0: np.ndarray, p1: np.ndarray,
    q0: np.ndarray, q1: np.ndarray,
) -> float:
    """Squared minimum distance between finite line segments p0-p1 and q0-q1."""
    d1 = p1 - p0
    d2 = q1 - q0
    r = p0 - q0
    a = float(np.dot(d1, d1))
    e = float(np.dot(d2, d2))
    f = float(np.dot(d2, r))

    if a < 1e-10:
        s = 0.0
        t = float(np.clip(f / e, 0.0, 1.0)) if e > 1e-10 else 0.0
    else:
        c = float(np.dot(d1, r))
        if e < 1e-10:
            t = 0.0
            s = float(np.clip(-c / a, 0.0, 1.0))
        else:
            b = float(np.dot(d1, d2))
            denom = a * e - b * b
            if abs(denom) > 1e-10:
                s = float(np.clip((b * f - c * e) / denom, 0.0, 1.0))
            else:
                s = 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0
                s = float(np.clip(-c / a, 0.0, 1.0))
            elif t > 1.0:
                t = 1.0
                s = float(np.clip((b - c) / a, 0.0, 1.0))

    closest_p = p0 + s * d1
    closest_q = q0 + t * d2
    diff = closest_p - closest_q
    return float(np.dot(diff, diff))


def _loop_intersects(
    start_np: np.ndarray,
    stop_np: np.ndarray,
    diameter: float,
    candidate_wires,
    candidate_loops,
) -> bool:
    """Return True if the loop capsule (start→stop, radius=diameter) overlaps anything.

    Uses an over-estimate (full diameter as clearance radius) so a gap is
    guaranteed when we find a clear angle.
    """
    for w in candidate_wires:
        wp1 = w.obj3d.start_position.as_numpy
        wp2 = w.obj3d.stop_position.as_numpy
        part = w.db_obj.part
        wire_r = float(part.od_mm) / 2.0 if (part and part.od_mm) else 0.5
        dist_sq = _seg_closest_dist_sq(start_np, stop_np, wp1, wp2)
        if dist_sq < (diameter + wire_r) ** 2:
            return True

    for lp in candidate_loops:
        lp1 = lp.obj3d.start_position.as_numpy
        lp2 = lp.obj3d.stop_position.as_numpy
        dist_sq = _seg_closest_dist_sq(start_np, stop_np, lp1, lp2)
        if dist_sq < (diameter * 2.0) ** 2:
            return True

    return False


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class AddWireServiceLoopHandler(_handler_base.HandlerBase):
    """Handle interactive placement of wire service loops on wires.

    No part selection — the loop inherits the wire's own part (wire type).
    Hovering over any wire shows a preview sized to the wire OD.  A single
    click splits the wire and inserts the service loop.

    The optional *wire_or_legacy* argument accepts either a Wire (pre-snap
    target from context menus) or an integer (legacy part_id — ignored).
    """
    obj: "_wire_service_loop.WireServiceLoop | None" = None

    def __init__(self, mainframe: "_ui.MainFrame", wire_or_legacy=None):
        super().__init__(mainframe, None)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))

        self._snapped_wire: "_wire.Wire | None" = None
        self._snapped_angle: "_angle.Angle | None" = None

        self._highlight_all_wires()

        # If a Wire was passed (e.g., from the wire context menu), the preview
        # will be created on the first hover over that wire.  Integers (legacy
        # part_id from old call sites) are intentionally ignored.

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _highlight_all_wires(self):
        for w in self.mainframe.project.wires:
            w.identify(self._highlight_material)

    def _clear_wire_highlights(self):
        for w in self.mainframe.project.wires:
            w.identify(None)

    def _wire_diameter(self, wire: "_wire.Wire") -> float:
        part_id = wire.db_obj.part_id
        if part_id is None:
            return 2.0
        part = self.mainframe.global_db.wires_table[part_id]
        return max(0.5, float(part.od_mm)) if (part and part.od_mm) else 2.0

    def _find_best_angle(
        self,
        wire_angle: "_angle.Angle",
        start_pos: _point.Point,
        diameter: float,
        wire: "_wire.Wire",
    ) -> np.ndarray:
        """Return a [w,x,y,z] quaternion that minimises intersections.

        Tries 16 orientations (22.5° increments) by twisting around the
        wire's local Z axis.  Returns the first non-intersecting orientation,
        or the zero-twist quaternion if none is found.
        """
        q_base = np.array(wire_angle.as_quat_float, dtype=np.float64)
        vbo = _cylinder_helix.create_vbo()
        scale = _point.Point(diameter, diameter, diameter)

        candidate_wires = [w for w in self.mainframe.project.wires if w is not wire]
        candidate_loops = list(self.mainframe.project.wire_service_loops)

        start_np = start_pos.as_numpy

        for step in range(16):
            theta = step * (2.0 * math.pi / 16.0)
            hw = math.cos(theta / 2.0)
            hz = math.sin(theta / 2.0)
            # Twist around local Z axis
            q_twist = np.array([hw, 0.0, 0.0, hz], dtype=np.float64)
            q_cand = _quat_mul(q_base, q_twist)

            ang = _angle.Angle.from_quat(q_cand.tolist())
            stop_local = vbo.endpoint.copy()
            stop_local *= scale
            stop_local @= ang
            stop_local += start_pos
            stop_np = stop_local.as_numpy

            if not _loop_intersects(start_np, stop_np, diameter,
                                    candidate_wires, candidate_loops):
                return q_cand

        return q_base  # no clear angle found — use zero twist

    def _create_preview(
        self,
        wire: "_wire.Wire",
        position: _point.Point,
        wire_angle: "_angle.Angle",
    ):
        """Delete any existing preview and build a new one at *position*."""
        if self.obj is not None:
            self.obj.delete()
            self.obj = None

        diameter = self._wire_diameter(wire)
        q_arr = np.array(wire_angle.as_quat_float, dtype=np.float64)
        stop_pos = _compute_stop(position, wire_angle, diameter)

        p_start_db = self.ptables.pjt_points3d_table.insert(
            position.x, position.y, position.z)
        p_stop_db = self.ptables.pjt_points3d_table.insert(
            stop_pos.x, stop_pos.y, stop_pos.z)

        loop_db = self.ptables.pjt_wire_service_loops_table.insert(
            p_start_db.db_id, p_stop_db.db_id,
            wire.db_obj.part_id, wire.db_obj.circuit_id,
            True, q_arr)

        self.obj = _wire_service_loop.WireServiceLoop(self.mainframe, loop_db)
        self.obj.identify(self._preview_material)
        self._snapped_wire = wire
        self._snapped_angle = wire_angle

    def _update_preview(
        self,
        position: _point.Point,
        wire_angle: "_angle.Angle",
        diameter: float,
    ):
        """Slide the existing preview to a new position on the same wire."""
        if self.obj is None:
            return

        stop_pos = _compute_stop(position, wire_angle, diameter)

        start_p = self.obj.obj3d.start_position
        stop_p = self.obj.obj3d.stop_position

        start_p += position - start_p
        stop_p += stop_pos - stop_p

        self._snapped_angle = wire_angle

    # ------------------------------------------------------------------
    # Handler protocol
    # ------------------------------------------------------------------

    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)
        wire = selected if isinstance(selected, _wire.Wire) else None

        if wire is None or wire.db_obj.part_id is None:
            if self.obj is not None:
                self.obj.obj3d.is_visible = False
            return

        position, wire_angle = wire.obj3d.get_closest_point(mouse_pos)

        if None in (position, wire_angle):
            if self.obj is not None:
                self.obj.obj3d.is_visible = False
            return

        if wire is not self._snapped_wire:
            self._create_preview(wire, position, wire_angle)
        else:
            diameter = self._wire_diameter(wire)
            self._update_preview(position, wire_angle, diameter)

        if self.obj is not None:
            self.obj.obj3d.is_visible = True

    def release_capture(self):
        if self._finalized:
            return
        if self._captured_position is None:
            return
        if self._snapped_wire is None or self.obj is None:
            return

        self._clear_wire_highlights()
        self._finalized = True

        wire = self._snapped_wire

        if wire.db_obj.part_id is None:
            self.obj.delete()
            self.obj = None
            return

        position, wire_angle = wire.obj3d.get_closest_point(self._captured_position)

        if None in (position, wire_angle):
            self.obj.delete()
            self.obj = None
            return

        diameter = self._wire_diameter(wire)

        # Find the orientation around the wire axis that avoids intersections.
        q_arr = self._find_best_angle(wire_angle, position, diameter, wire)
        best_angle = _angle.Angle.from_quat(q_arr.tolist())
        stop_pos = _compute_stop(position, best_angle, diameter)

        # Update the preview's positions and angle to the committed values.
        start_p = self.obj.obj3d.start_position
        stop_p = self.obj.obj3d.stop_position
        start_p += position - start_p
        stop_p += stop_pos - stop_p
        self.obj.db_obj.angle = q_arr

        loop_start_id = int(self.obj.obj3d.start_position.db_id[:-2])
        loop_stop_id = int(self.obj.obj3d.stop_position.db_id[:-2])

        original_start_id = int(wire.obj3d.start_position.db_id[:-2])
        original_stop_id = int(wire.obj3d.stop_position.db_id[:-2])
        part_id = wire.db_obj.part_id
        circuit_id = wire.db_obj.circuit_id

        # Wire 1: original_start → loop_start
        wire1_db = self.ptables.pjt_wires_table.insert(
            part_id, circuit_id,
            original_start_id, loop_start_id,
            None, None, True, False, None, None, False)

        # Wire 2: loop_stop → original_stop
        wire2_db = self.ptables.pjt_wires_table.insert(
            part_id, circuit_id,
            loop_stop_id, original_stop_id,
            None, None, True, False, None, None, False)

        self.mainframe.project.add_wire(_wire.Wire(self.mainframe, wire1_db))
        self.mainframe.project.add_wire(_wire.Wire(self.mainframe, wire2_db))
        wire.delete()

        self.obj.identify(None)
        self.mainframe.project.add_wire_service_loop(self.obj)
        self.obj = None

    def cancel(self):
        self._clear_wire_highlights()
        if self.obj is not None:
            self.obj.delete()
            self.obj = None
