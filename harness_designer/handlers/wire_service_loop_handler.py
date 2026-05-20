# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_service_loop as _wire_service_loop
from ..objects import wire as _wire
from ..shapes import cylinder_helix as _cylinder_helix
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


def _get_wire_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _wire.Wire | None:
    """
    Check if the mouse is over a wire object.

    Returns:
        Wire object if found, None otherwise
    """
    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _wire.Wire):
        return selected

    return None


def _compute_stop_point(
    start_pos: _point.Point,
    wire_angle: _angle.Angle,
    diameter: float
) -> _point.Point:
    """
    Compute the exact world-space stop point of the service loop helix.

    The helix VBO is unit-scale (diameter=1.0). The stop point is stored
    as vbo.endpoint in local space. We scale it by the wire diameter then
    rotate and translate to get the world position, matching exactly what
    the 3D object does at render time.
    """
    vbo = _cylinder_helix.create_vbo()
    scale = _point.Point(diameter, diameter, diameter)

    # vbo.endpoint is a Point in unit local space
    # apply scale -> rotate by wire angle -> translate to start position
    stop_local = vbo.endpoint.copy()
    stop_local *= scale
    stop_local @= wire_angle
    stop_local += start_pos

    return stop_local


class AddWireServiceLoopHandler(_handler_base.HandlerBase):
    obj: _wire_service_loop.WireServiceLoop = None

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)

        self.wire = None
        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))
        self._terminal_material = _materials.Plastic(
            _color.Color(*Config.add_object.terminal_highlight))

    def release_capture(self) -> None:
        raise NotImplementedError

    def _get_wire_diameter(self) -> float:
        part = self.mainframe.project.gtables.wires_table[self.part_id]
        return float(part.od_mm) if part.od_mm else 2.0

    def _make_preview_loop(self, position: _point.Point, wire_angle: _angle.Angle,
                           circuit_id: int | None) -> _wire_service_loop.WireServiceLoop:

        diameter = self._get_wire_diameter()
        stop_pos = _compute_stop_point(position, wire_angle, diameter)

        quat = np.array(wire_angle.as_quat_float)

        p3d_start = self.ptables.pjt_points3d_table.insert(
            position.x, position.y, position.z)

        p3d_stop = self.ptables.pjt_points3d_table.insert(
            stop_pos.x, stop_pos.y, stop_pos.z)

        loop_db = self.ptables.pjt_wire_service_loops_table.insert(
            start_point3d_id=p3d_start.db_id,
            stop_point3d_id=p3d_stop.db_id,
            part_id=self.part_id,
            circuit_id=circuit_id,
            is_visible=True,
            quat=quat
        )

        loop = _wire_service_loop.WireServiceLoop(self.mainframe, loop_db)
        loop.obj3d._material = self._preview_material

        self.mainframe.add_object(loop)

        return loop

    def _update_preview_position(self, position: _point.Point, wire_angle: _angle.Angle):

        if self.obj is None:
            return

        diameter = self._get_wire_diameter()
        stop_pos = _compute_stop_point(position, wire_angle, diameter)

        # Move start
        cur_start = self.obj.obj3d.start_position
        delta = position - cur_start
        cur_start += delta

        # Move stop
        cur_stop = self.obj.obj3d.stop_position
        delta = stop_pos - cur_stop
        cur_stop += delta

        # Update quaternion to match wire angle at this position
        quat = np.array(wire_angle.as_quat_float)
        self.obj.db_obj.table.update(
            self.obj.db_obj.db_id, quat=str(quat.tolist()))

    def _delete_preview(self):
        """Remove the preview loop and clean up its DB rows."""
        if self.obj is not None:
            self.obj.delete()
            self.obj = None

    def hover(self, mouse_pos: _point.Point):
        """
        Track mouse over wires — highlight wire and show/move preview loop.
        The wire is never touched here, only the preview object moves.
        """
        wire = _get_wire_at_mouse(mouse_pos, self.camera)

        if wire is None:
            # Mouse left all wires — clear highlight and preview
            if self.wire is not None:
                self.wire.identify(None)
                self.wire = None

            self._delete_preview()
            return

        # Get closest point on the wire and wire direction at that point
        position, wire_angle = _utils.get_closest_point_on_wire(
            mouse_pos, self.camera, wire)

        if None in (position, wire_angle):
            if self.wire is not None:
                self.wire.identify(None)
                self.wire = None

            self._delete_preview()
            return

        # Highlight the wire if it changed
        if wire != self.wire:
            if self.wire is not None:
                self.wire.identify(None)

            wire.identify(self.WIRE_HIGHLIGHT)
            self.wire = wire

        # Create preview on first hover over this wire, or update position
        if self.obj is None:
            self.obj = self._make_preview_loop(
                position, wire_angle, wire.db_obj.circuit_id)
        else:
            self._update_preview_position(position, wire_angle)

    def start(self, mouse_pos: _point.Point):
        """
        Place the service loop on click.

        The wire is broken at the preview position (same pattern as splice
        handler). The loop's start point shares the Point from the break
        so the callback chain keeps the loop root pinned to the wire end.
        """
        wire = _get_wire_at_mouse(mouse_pos, self.camera)

        if wire is None:
            return

        position, wire_angle = _utils.get_closest_point_on_wire(
            mouse_pos, self.camera, wire)

        if None in (position, wire_angle):
            return

        # Remove the preview — we are about to create the real object
        self._delete_preview()

        if self.wire is not None:
            self.wire.identify(None)
            self.wire = None

        # ── Break the wire at the loop position ──────────────────────────
        # Mirror the splice handler: create a shared Point at the break
        # position, split the wire into two segments, then reference that
        # shared Point as the loop's start so callbacks stay connected.

        original_start_db_id = int(wire.obj3d.start_position.db_id[:-2])
        original_stop_db_id = int(wire.obj3d.stop_position.db_id[:-2])
        part_id = wire.db_obj.part_id
        circuit_id = wire.db_obj.circuit_id

        # Shared point at the break — referenced by both wire segments
        # and by the loop start
        shared_p3d = self.ptables.pjt_points3d_table.insert(
            position.x, position.y, position.z)
        shared_db_id = shared_p3d.db_id

        # Wire segment 1: original start → shared point
        wire1_db = self.ptables.pjt_wires_table.insert(
            part_id=part_id,
            circuit_id=circuit_id,
            start_point3d_id=original_start_db_id,
            stop_point3d_id=shared_db_id,
            start_point2d_id=None,
            stop_point2d_id=None,
            is_visible3d=True,
            is_visible2d=False,
            layer_view_point_id=None,
            layer_id=None,
            is_filler_wire=False
        )

        # Wire segment 2: shared point → original stop
        wire2_db = self.ptables.pjt_wires_table.insert(
            part_id=part_id,
            circuit_id=circuit_id,
            start_point3d_id=shared_db_id,
            stop_point3d_id=original_stop_db_id,
            start_point2d_id=None,
            stop_point2d_id=None,
            is_visible3d=True,
            is_visible2d=False,
            layer_view_point_id=None,
            layer_id=None,
            is_filler_wire=False
        )

        wire1_obj = _wire.Wire(self.mainframe, wire1_db)
        wire2_obj = _wire.Wire(self.mainframe, wire2_db)

        self.mainframe.project.add_wire(wire1_obj)
        self.mainframe.project.add_wire(wire2_obj)

        wire.delete()

        # ── Compute exact stop point from VBO endpoint ────────────────────
        diameter = self._get_wire_diameter()
        stop_pos = _compute_stop_point(position, wire_angle, diameter)

        p3d_stop = self.ptables.pjt_points3d_table.insert(
            stop_pos.x, stop_pos.y, stop_pos.z)

        quat = np.array(wire_angle.as_quaternion_float)

        # Loop start references the SHARED point — same instance as wire
        # segment boundary, so the callback system keeps them in sync
        loop_db = self.ptables.pjt_wire_service_loops_table.insert(
            start_point3d_id=shared_db_id,
            stop_point3d_id=p3d_stop.db_id,
            part_id=self.part_id,
            circuit_id=circuit_id,
            is_visible=True,
            quat=quat
        )

        loop = _wire_service_loop.WireServiceLoop(self.mainframe, loop_db)
        self.mainframe.project.add_wire_service_loop(loop)

    def finalize(self, mouse_pos: _point.Point):
        # For this handler start() does the placement on first click.
        # finalize() is called on the second click — clean up any
        # lingering preview if the user managed to click twice.
        self._delete_preview()

        if self.wire is not None:
            self.wire.identify(None)
            self.wire = None
