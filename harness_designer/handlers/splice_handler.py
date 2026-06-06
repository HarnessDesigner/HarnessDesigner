# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for inserting splices into wires.
"""

from typing import TYPE_CHECKING
from PySide6.QtWidgets import QDialog

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..geometry import angle as _angle
from ..geometry import line as _line
from ..gl.canvas3d import object_picker as _object_picker
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from ..objects import wire as _wire
from ..objects import splice as _splice
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui
    from ..database.global_db import splice as _db_splice


Config = _config.Config.colors


def _get_wire_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _wire.Wire | None:

    """
    Check if mouse is over a wire object.

    Returns:
        Wire object if found, None otherwise
    """
    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _wire.Wire):
        return selected

    return None


class AddSpliceHandler(_handler_base.HandlerBase):
    """Handle interactive insertion of splice objects into existing wires.
    """
    obj: _splice.Splice = None

    def __init__(self, mainframe: "_ui.MainFrame", wire: _wire.Wire = None):
        """Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """
        self.wire = wire
        part_id = mainframe.editor_db.splices.GetValue()

        if wire is None:
            compat_splices = []
        else:
            size = wire.db_obj.part.conductor_dia_mm
            mainframe.global_db.splices_table.execute(
                'SELECT part_number FROM splices WHERE wire_size_cross_min <= ?;',
                (size,))

            rows = mainframe.global_db.splices_table.fetchall()
            compat_splices = [row[0] for row in rows]

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SplicesPage, title='Add Splice',
                table=mainframe.global_db.splices_table, initial_results=compat_splices)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        self._compat_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))

        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.splice_highlight))

        self.part: "_db_splice.Splice" = None
        self._attached_wire: _wire.Wire = wire
        if part_id is None:
            self._finalized = True
        else:
            self.set_part(part_id)

    def set_part(self, part_id):
        self.part = self.mainframe.global_db.splices_table[part_id]

        size = self.part.wire_size_cross_min

        for wire in self.mainframe.project.wires:
            if wire.db_obj.part.size_mm2 >= size:
                wire.identify(self._compat_material)
            else:
                wire.identify(self._highlight_material)

        if self.obj is not None:
            self.obj.delete()

        if self.wire is not None:
            self.wire.identify(self._highlight_material)

            line = _line.Line(self.wire.db_obj.start_position3d, self.wire.db_obj.stop_position3d)
            stop_point = line.point_from_start(self.part.length)
            branch_point = line.point_from_start(self.part.length / 2)

            x, y, z = self.wire.db_obj.start_position3d.as_float
            start_point_db = self.ptables.pjt_points3d_table.insert(x, y, z)
            stop_point_db = self.ptables.pjt_points3d_table.insert(*stop_point.as_float)
            branch_point_db = self.ptables.pjt_points3d_table.insert(*branch_point.as_float)

            db_obj = self.ptables.pjt_splices_table.insert(
                part_id, start_point_db.db_id, stop_point_db.db_id,
                branch_point_db.db_id, None, None)

            self.obj = _splice.Splice(self.mainframe, db_obj)
            self.obj.identify(self._preview_material)

    def hover(self, mouse_pos: _point.Point):
        """
        Track mouse over wires — highlight wire and show/update preview splice.
        The wire is never modified here.
        """

        if self.wire is None:
            wire = _get_wire_at_mouse(mouse_pos, self.camera)
            self._attached_wire = wire
        else:
            wire = self.wire

        if wire is None:
            return

        point, angle = _utils.get_closest_point_on_wire(mouse_pos, self.camera, wire)

        point_delta = point - self.obj.db_obj.start_position3d

        start_position3d = self.obj.db_obj.start_position3d
        stop_position3d = self.obj.db_obj.stop_position3d
        branch_position3d = self.obj.db_obj.branch_position3d

        start_position3d += point_delta
        stop_position3d += point_delta
        branch_position3d += point_delta

    def release_capture(self):
        """
        Place the splice on click.

        Removes the preview, breaks the wire at the splice centre position,
        and creates the real splice whose start/stop points share the wire
        segment boundary Points so the callback chain stays intact.
        """
        if self._finalized:
            return

        if self._captured_position is None:
            return

        if self._attached_wire is None:
            return

        for wire in self.mainframe.project.wires:
            wire.identify(None)

        self._finalized = True

        wire = self._attached_wire
        position, wire_angle = _utils.get_closest_point_on_wire(
            self._captured_position, self.camera, wire)

        if None in (position, wire_angle):
            self.obj.delete()
            return

        splice_start_p3d = self.obj.db_obj.start_position3d
        splice_stop_p3d = self.obj.db_obj.stop_position3d
        branch_p3d = self.obj.db_obj.branch_position3d

        line = _line.Line(splice_start_p3d, splice_stop_p3d)
        splice_length = line.length()

        # ── Compute splice endpoint positions ────────────────────────────
        direction = wire_angle.as_matrix_numpy[:, 2]
        half_length = splice_length / 2.0

        start_xyz = position.as_numpy - direction * half_length
        stop_xyz = position.as_numpy + direction * half_length
        branch_xyz = position.as_numpy

        # ── Get original wire data ───────────────────────────────────────
        original_start_db_id = int(wire.obj3d.start_position.db_id[:-2])
        original_stop_db_id = int(wire.obj3d.stop_position.db_id[:-2])
        part_id = wire.db_obj.part_id
        circuit_id = wire.db_obj.circuit_id

        # ── Create splice points ─────────────────────────────────────────
        # start and stop are the wire-facing stubs — they become shared
        # boundary points with the two new wire segments so the callback
        # system keeps the splice pinned to the wire ends when moved

        splice_start_db_id = splice_start_p3d.db_id[:-2]
        splice_stop_db_id = splice_stop_p3d.db_id[:-2]

        # ── Create first wire segment: original start → splice start ─────
        wire1_db = self.ptables.pjt_wires_table.insert(
            part_id=part_id,
            circuit_id=circuit_id,
            start_point3d_id=original_start_db_id,
            stop_point3d_id=splice_start_db_id,
            start_point2d_id=None,
            stop_point2d_id=None,
            is_visible3d=True,
            is_visible2d=False,
            layer_view_point_id=None,
            layer_id=None,
            is_filler_wire=False
        )

        # ── Create second wire segment: splice stop → original stop ──────
        wire2_db = self.ptables.pjt_wires_table.insert(
            part_id=part_id,
            circuit_id=circuit_id,
            start_point3d_id=splice_stop_db_id,
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

        self.obj.db_obj.circuit_id = circuit_id
        self.mainframe.project.add_splice(self.obj)
