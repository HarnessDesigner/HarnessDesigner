# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for inserting splices into wires."""

import numpy as np
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QDialog

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from ..objects import wire as _wire
from ..objects import splice as _splice
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors


def _wire_fits(splice_part, wire) -> bool:
    """
    Return True when the wire's AWG falls within the splice's accepted range.
    """
    part = wire.db_obj.part
    if part is None:
        return False

    wire_awg = part.size_awg
    if wire_awg is None:
        return False

    awg_min = splice_part.wire_size_awg_min
    awg_max = splice_part.wire_size_awg_max
    # AWG is inverse: higher number = smaller wire.
    # awg_min is the MINIMUM awg number the splice accepts (largest wire).
    # awg_max is the MAXIMUM awg number the splice accepts (smallest wire).
    if awg_min is not None and wire_awg < awg_min:
        return False

    if awg_max is not None and wire_awg > awg_max:
        return False

    return True


class AddSpliceHandler(_handler_base.HandlerBase):
    """
    Handle interactive insertion of splice objects into existing wires.
    """
    obj: _splice.Splice = None

    def __init__(self, mainframe: "_ui.MainFrame", wire: "_wire.Wire | None" = None):
        part_id = mainframe.editor_db.editor.splices.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SplicesPage, title='Add Splice',
                table=mainframe.global_db.splices_table)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        self._compat_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))

        self._snapped_wire: "_wire.Wire | None" = None
        self.part: "_db_splice.Splice | None" = None

        if part_id is None:
            self._finalized = True
            return

        self.part = mainframe.global_db.splices_table[part_id]
        self._highlight_compatible_wires()

        # If a wire was passed in (from a context menu), immediately lock to it.
        if wire is not None and _wire_fits(self.part, wire):
            self._create_preview(wire)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _highlight_compatible_wires(self):
        for w in self.mainframe.project.wires:
            if _wire_fits(self.part, w):
                w.identify(self._compat_material)

    def _clear_wire_highlights(self):
        for w in self.mainframe.project.wires:
            w.identify(None)

    def _create_preview(self, wire: "_wire.Wire"):
        """
        Tear down any existing preview and build a new one locked to *wire*.
        """

        if self.obj is not None:
            self.obj.delete()
            self.obj = None

        p1 = wire.obj3d.start_position.as_numpy
        p2 = wire.obj3d.stop_position.as_numpy
        seg = p2 - p1
        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-8:
            return

        direction = seg / seg_len
        center = (p1 + p2) / 2.0
        half = float(self.part.length) / 2.0

        start_np = center - direction * half
        stop_np = center + direction * half

        start_db = self.ptables.pjt_points3d_table.insert(*start_np.tolist())
        stop_db = self.ptables.pjt_points3d_table.insert(*stop_np.tolist())
        branch_db = self.ptables.pjt_points3d_table.insert(*center.tolist())

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        db_obj = self.ptables.pjt_splices_table.insert(
            self.part_id, name,
            start_db.db_id, stop_db.db_id, branch_db.db_id,
            None, None)

        self.obj = _splice.Splice(self.mainframe, db_obj)
        self.obj.identify(self._preview_material)
        self._snapped_wire = wire

    # ------------------------------------------------------------------
    # Handler protocol
    # ------------------------------------------------------------------

    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)
        wire = selected if isinstance(selected, _wire.Wire) else None

        if wire is None or not _wire_fits(self.part, wire):
            if self.obj is not None:
                self.obj.obj3d.is_visible = False
            self._snapped_wire = None
            return

        # Wire changed — rebuild preview so the angle is correct for this wire.
        if wire is not self._snapped_wire:
            self._create_preview(wire)

        if self.obj is None:
            return

        point, _ = wire.obj3d.get_closest_point(mouse_pos)
        if point is None:
            return

        # Translate the three preview points to follow the mouse along the wire.
        start_p = self.obj.db_obj.start_position3d
        stop_p = self.obj.db_obj.stop_position3d
        branch_p = self.obj.db_obj.branch_position3d
        delta = point - branch_p
        start_p += delta
        stop_p += delta
        branch_p += delta

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

        position, wire_angle = wire.obj3d.get_closest_point(
            self._captured_position)

        if None in (position, wire_angle):
            self.obj.delete()
            return

        # Refine splice point positions to the exact click location.
        direction = wire_angle.as_matrix_numpy[:, 2]
        half = float(self.part.length) / 2.0

        start_np = position.as_numpy - direction * half
        stop_np = position.as_numpy + direction * half

        start_p = self.obj.db_obj.start_position3d
        stop_p = self.obj.db_obj.stop_position3d
        branch_p = self.obj.db_obj.branch_position3d

        target_start = _point.Point(*start_np.tolist())
        target_stop = _point.Point(*stop_np.tolist())

        start_p += target_start - start_p
        stop_p += target_stop - stop_p
        branch_p += position - branch_p

        # IDs for the DB records
        original_start_id = int(wire.obj3d.start_position.db_id[:-2])
        original_stop_id = int(wire.obj3d.stop_position.db_id[:-2])
        splice_start_id = int(start_p.db_id[:-2])
        splice_stop_id = int(stop_p.db_id[:-2])

        circuit_id = wire.db_obj.circuit_id
        part_id = wire.db_obj.part_id

        # Wire 1: original start → splice start
        wire1_db = self.ptables.pjt_wires_table.insert(
            part_id, circuit_id,
            original_start_id, splice_start_id,
            None, None, True,
            False, None, None, False)

        # Wire 2: splice stop → original stop
        wire2_db = self.ptables.pjt_wires_table.insert(
            part_id, circuit_id,
            splice_stop_id, original_stop_id,
            None, None, True,
            False, None, None, False)

        self.mainframe.project.add_wire(_wire.Wire(self.mainframe, wire1_db))
        self.mainframe.project.add_wire(_wire.Wire(self.mainframe, wire2_db))

        wire.delete()

        self.obj.db_obj.circuit_id = circuit_id
        self.mainframe.project.add_splice(self.obj)
        self.obj = None

    def cancel(self):
        self._clear_wire_highlights()
        if self.obj is not None:
            self.obj.delete()
            self.obj = None
