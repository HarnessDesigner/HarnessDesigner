# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-snapping splice placement for the schematic editor.

Per explicit direction: the actual wire-fork cut still goes through the
wire's own 3D geometry (``handlers.wire_topology.split_wire_at_point``,
the same call ``add_handlers.editor_3d.splice`` uses -- that function
only ever accepts a 3D cut position, and extending it to a genuinely
2D-native cut wasn't wanted for this pass). The schematic-side click is
mapped onto the wire's 3D chord by fractional arc-length: :func:`
closest_point_on_wire_2d` finds where the cursor landed along the
wire's full 2D polyline (0.0 at the true start, 1.0 at the true stop,
walking through every waypoint in between) and that same fraction is
used to interpolate a point on the *3D* straight line between the
wire's own 3D start/stop (interior 3D waypoints, if any, are not
accounted for -- an acceptable simplification here, matching this
mechanism's own already-established "no independent 2D geometry to go
by" fallback for a freshly split wire's own 2D endpoint -- see
``split_wire_at_point``'s own docstring). The splice's own rendered 2D
position is the real clicked point, not reinterpolated from the
fraction.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from ...handlers import splice_handler as _splice_handler
from ...handlers import wire_topology as _wire_topology
from ...objects import wire as _wire
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


@_check_types.do
def closest_point_on_wire_2d(wire: "_wire.Wire", world_x: float, world_z: float):
    """Closest point on *wire*'s full 2D polyline (true start, through
    every waypoint, to true stop) to ``(world_x, world_z)``.

    :returns: ``(t, (px, pz))`` -- *t* the fractional arc-length
        position along the whole path (0.0 at the true start, 1.0 at
        the true stop), and the closest point itself.
    """
    objschematic = wire.objschematic
    waypoints = list(wire.db_obj.waypoints2d)

    points = [objschematic._p1] + [wp.point for wp in waypoints] + [objschematic._p2]  # NOQA
    positions = [(float(p.x), float(p.z)) for p in points]

    seg_lengths = []
    total = 0.0
    for i in range(len(positions) - 1):
        ax, az = positions[i]
        bx, bz = positions[i + 1]
        length = math.hypot(bx - ax, bz - az)
        seg_lengths.append(length)
        total += length

    if total < 1e-9:
        return 0.0, positions[0]

    best_dist = math.inf
    best_t = 0.0
    best_point = positions[0]
    cum = 0.0

    for i, length in enumerate(seg_lengths):
        ax, az = positions[i]
        bx, bz = positions[i + 1]

        if length < 1e-9:
            frac = 0.0
        else:
            frac = max(0.0, min(1.0, (
                (world_x - ax) * (bx - ax) + (world_z - az) * (bz - az)) / (length * length)))

        px, pz = ax + frac * (bx - ax), az + frac * (bz - az)
        dist = math.hypot(world_x - px, world_z - pz)

        if dist < best_dist:
            best_dist = dist
            best_t = (cum + frac * length) / total
            best_point = (px, pz)

        cum += length

    return best_t, best_point


class Splice(_base.AddHandlerBase):
    """Wire-snapping splice placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part_id: bytes,
        part, preview_material, compat_material
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part_id = part_id
        self._part = part
        self._preview_material = preview_material
        self._compat_material = compat_material
        self._snapped_wire = None
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.objschematic

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize(current_pos)
            return True

        return False

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        picked = _object_picker.find_object(
            mouse_pos, self.mainframe.editor2d.editor.objects, self.camera, self._get_view_object)

        wire = picked if isinstance(picked, _wire.Wire) else None

        if wire is None or not _splice_handler._wire_fits(self._part, wire):  # NOQA
            if self.target is not None:
                self.target.objschematic.is_visible = False

            self._snapped_wire = None
            return

        if wire is not self._snapped_wire:
            self._recreate_preview(wire)

        if self.target is None:
            return

        world_pos = self.camera.screen_to_world(mouse_pos)
        _t, (px, pz) = closest_point_on_wire_2d(wire, float(world_pos.x), float(world_pos.z))

        position2d = self.target.db_obj.position2d
        with position2d:
            position2d.x = px
            position2d.z = pz

        self.target.objschematic.is_visible = True

    @_check_types.do
    def _recreate_preview(self, wire: "_wire.Wire") -> None:
        from ...objects import splice as _splice_facade

        if self.target is not None:
            self.target.delete()
            self.target = None

        p1 = wire.obj3d.start_position.as_numpy
        p2 = wire.obj3d.stop_position.as_numpy
        seg = p2 - p1
        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-8:
            self._snapped_wire = None
            return

        direction = seg / seg_len
        center = (p1 + p2) / 2.0
        half = float(self._part.length) / 2.0

        start_np = center - direction * half
        stop_np = center + direction * half

        ptables = self.mainframe.project.ptables
        start_db = ptables.pjt_points3d_table.insert(*start_np.tolist())
        stop_db = ptables.pjt_points3d_table.insert(*stop_np.tolist())
        branch_db = ptables.pjt_points3d_table.insert(*center.tolist())
        point2d_db = ptables.pjt_points2d_table.insert(0.0, 0.0)

        name = f'{self._part.manufacturer.name} {self._part.part_number}'

        db_obj = ptables.pjt_splices_table.insert(
            self._part_id, name,
            start_db.db_id, stop_db.db_id, branch_db.db_id, point2d_db.db_id, None)

        facade = _splice_facade.Splice(self.mainframe, db_obj)
        facade.identify(self._preview_material)

        self.target = facade
        facade.objschematic._active_handler = self  # NOQA
        self.canvas.active_handler_obj = facade.objschematic

        self._snapped_wire = wire

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        if self._snapped_wire is None or self.target is None:
            return

        for w in self.mainframe.project.wires:
            w.identify(None)

        wire = self._snapped_wire

        world_pos = self.camera.screen_to_world(mouse_pos)
        t, (px, pz) = closest_point_on_wire_2d(wire, float(world_pos.x), float(world_pos.z))

        p1 = wire.obj3d.start_position.as_numpy
        p2 = wire.obj3d.stop_position.as_numpy
        position_np = p1 + t * (p2 - p1)

        seg = p2 - p1
        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-8:
            self.target.delete()
            self.target = None
            self._finalized = True
            return

        direction = seg / seg_len
        half = float(self._part.length) / 2.0

        start_np = position_np - direction * half
        stop_np = position_np + direction * half

        start_p = self.target.db_obj.start_position3d
        stop_p = self.target.db_obj.stop_position3d
        branch_p = self.target.db_obj.branch_position3d
        position2d = self.target.db_obj.position2d

        target_start = _point.Point(*start_np.tolist())
        target_stop = _point.Point(*stop_np.tolist())
        target_branch = _point.Point(*position_np.tolist())

        start_p += target_start - start_p
        stop_p += target_stop - stop_p
        branch_p += target_branch - branch_p

        with position2d:
            position2d.x = px
            position2d.z = pz

        splice_start_id = start_p.db_id[:-2]
        splice_stop_id = stop_p.db_id[:-2]

        circuit_id = wire.db_obj.circuit_id
        project = self.mainframe.project

        wire_before, wire_rest = _wire_topology.split_wire_at_point(
            project, wire, splice_start_id)

        wire_gap, wire_after = _wire_topology.split_wire_at_point(
            project, wire_rest, splice_stop_id)

        wire_gap.delete()

        self.target.db_obj.circuit_id = circuit_id
        self.target.set_siblings(wire_before, wire_after)
        wire_before.set_sibling(self.target, 'stop')
        wire_after.set_sibling(self.target, 'start')

        project.add_splice(self.target)

        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        for w in self.mainframe.project.wires:
            w.identify(None)

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
