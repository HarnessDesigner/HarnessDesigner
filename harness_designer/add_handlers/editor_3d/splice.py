# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-snapping splice placement for the 3D editor.

Ported from ``handlers.splice_handler.AddSpliceHandler`` -- the preview
splice is rebuilt (deleted and recreated) every time the wire it's
snapped to changes, exactly as the original did; the one thing that
changes here is bookkeeping ``self.target`` has to do every time that
happens, since this session's own ``_active_handler``/``canvas.
active_handler_obj`` pointers have to move to the new facade instance
along with it (``objects.objects_3d.wire.Wire.start_add``'s free-space
case has an analogous "target facade may change mid-session" wrinkle
when merging into another wire; this is the same technique).

``objects.objects_3d.splice.Splice.start_add`` builds a placeholder
(invisible, degenerate) preview immediately when no wire was given up
front (toolbar-started placement, matching every other migrated type's
"real object from the moment placement begins" rule) -- the first hover
over a compatible wire replaces it with a real one anyway, via
:meth:`Splice._recreate_preview`.
"""

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
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


class Splice(_base.AddHandlerBase):
    """Wire-snapping splice placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part_id: bytes,
        part, preview_material, compat_material, snapped_wire=None
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part_id = part_id
        self._part = part
        self._preview_material = preview_material
        self._compat_material = compat_material
        self._snapped_wire = snapped_wire
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.obj3d

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
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)

        wire = picked if isinstance(picked, _wire.Wire) else None

        if wire is None or not _splice_handler._wire_fits(self._part, wire):  # NOQA
            if self.target is not None:
                self.target.obj3d.is_visible = False

            self._snapped_wire = None
            return

        if wire is not self._snapped_wire:
            self._recreate_preview(wire)

        if self.target is None:
            return

        point, _angle, _idx = wire.obj3d.get_closest_point(mouse_pos)
        if point is None:
            return

        start_p = self.target.db_obj.start_position3d
        stop_p = self.target.db_obj.stop_position3d
        branch_p = self.target.db_obj.branch_position3d
        delta = point - branch_p
        start_p += delta
        stop_p += delta
        branch_p += delta

        self.target.obj3d.is_visible = True

    @_check_types.do
    def _recreate_preview(self, wire: "_wire.Wire") -> None:
        """Tear down the current preview (if any -- the placeholder
        built at arm time, or whichever wire's preview this replaces)
        and build a new one locked to *wire*, re-arming this same
        session on the new facade's own view instance.
        """
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

        name = f'{self._part.manufacturer.name} {self._part.part_number}'

        db_obj = ptables.pjt_splices_table.insert(
            self._part_id, name,
            start_db.db_id, stop_db.db_id, branch_db.db_id, None, None)

        facade = _splice_facade.Splice(self.mainframe, db_obj)
        facade.identify(self._preview_material)

        self.target = facade
        facade.obj3d._active_handler = self  # NOQA
        self.canvas.active_handler_obj = facade.obj3d

        self._snapped_wire = wire

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        if self._snapped_wire is None or self.target is None:
            return

        for w in self.mainframe.project.wires:
            w.identify(None)

        wire = self._snapped_wire

        position, wire_angle, _idx = wire.obj3d.get_closest_point(mouse_pos)

        if position is None or wire_angle is None:
            self.target.delete()
            self.target = None
            self._finalized = True
            return

        direction = wire_angle.as_matrix_numpy[:, 2]
        half = float(self._part.length) / 2.0

        start_np = position.as_numpy - direction * half
        stop_np = position.as_numpy + direction * half

        start_p = self.target.db_obj.start_position3d
        stop_p = self.target.db_obj.stop_position3d
        branch_p = self.target.db_obj.branch_position3d

        target_start = _point.Point(*start_np.tolist())
        target_stop = _point.Point(*stop_np.tolist())

        start_p += target_start - start_p
        stop_p += target_stop - stop_p
        branch_p += position - branch_p

        splice_start_id = start_p.db_id[:-2]
        splice_stop_id = stop_p.db_id[:-2]

        circuit_id = wire.db_obj.circuit_id
        project = self.mainframe.project

        # Fork the wire around the splice's own body -- wire_before keeps
        # the original wire's own start (through splice_start_id);
        # splitting the resulting "after" piece again at splice_stop_id
        # discards the middle span, which the splice's own body occupies
        # instead of a wire.
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
