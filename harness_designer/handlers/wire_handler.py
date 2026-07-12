# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for placing wires between compatible endpoints.

Two-click workflow:
  Phase 0 – hover highlights valid start targets; click sets the start point.
  Phase 1 – live preview wire tracks the mouse; second click finalises placement.

Terminal-attached start (*terminal* argument given):
  Phase 0 is skipped — a part-search dialog (pre-filtered to wires whose
  diameter fits the terminal's crimp range) opens immediately, and the
  preview wire starts pinned to the terminal, straight into phase 1.
  Invoke via :func:`objects.objects3d.menu_ops.start_handler`.

Start-click variants:
  WireLayout  → part_id inherited from the attached wire; start at layout position.
  Wire end    → extension mode: the existing wire endpoint moves to the second click
                position, constrained to the wire's current direction.
  Terminal    → compatibility check (diameter + combined cross-section); circuit_id
                inherited.
  Free space  → new start point at focal-plane position.

End-click variants (phase 1, non-extension):
  Terminal          → compat check; wire inherits circuit_id if not already set.
  WireLayout at end → must be an endpoint (not a split mid-point) with matching part_id.
  Splice            → wire connects to branch_position.
  Free space        → new stop point at focal-plane position.
"""

import numpy as np
from PySide6.QtWidgets import QLabel, QDialog
from PySide6.QtCore import Qt
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import terminal as _terminal
from ..objects import splice as _splice
from ..objects import wire as _wire
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors

_SNAP_THRESHOLD = 5.0


class _IncompatOverlay(QLabel):
    """Floating label shown near the cursor when a terminal is incompatible."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(
            'background-color: rgba(180,0,0,200); color: white;'
            ' padding: 4px 6px; border-radius: 3px;')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

    def show_message(self, mouse_pos, text):
        self.setText(text)
        self.adjustSize()
        self.move(int(mouse_pos.x) + 14, int(mouse_pos.y) + 14)
        self.show()
        self.raise_()

    def hide_message(self):
        if self.isVisible():
            self.hide()


def _wire_layout_end_wire(wire_layout_obj, project, part_id):
    """Return (wire, endpoint) if the layout sits at one endpoint of a wire with matching part_id.

    Returns (None, None) when the layout is mid-wire (split point, two wires share it)
    or when no wire with the given part_id is attached.
    """
    if part_id is None:
        return None, None

    layout_pos_id = wire_layout_obj.db_obj.position3d_id
    matching = []

    for w in project.wires:
        if not w.is_in_3dview:
            continue

        start_str = w.obj3d.start_position.db_id
        stop_str = w.obj3d.stop_position.db_id
        if start_str and int(start_str[:-2]) == layout_pos_id:
            matching.append((w, 'start'))

        elif stop_str and int(stop_str[:-2]) == layout_pos_id:
            matching.append((w, 'stop'))

    if len(matching) == 1:
        w, ep = matching[0]
        if w.db_obj.part_id == part_id:
            return w, ep

    return None, None


def _get_terminal_compat_pns(mainframe, terminal_obj):
    """Return wire part numbers whose outer diameter fits *terminal_obj*'s crimp range."""
    term_part = terminal_obj.db_obj.part
    if term_part is None:
        return []

    dia_min = term_part.wire_size_dia_min
    dia_max = term_part.wire_size_dia_max

    if dia_min is None and dia_max is None:
        return []

    table = mainframe.global_db.wires_table

    if dia_min is not None and dia_max is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=? AND od_mm<=?;',
            (dia_min, dia_max))
    elif dia_min is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=?;', (dia_min,))
    else:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm<=?;', (dia_max,))

    return [row[0] for row in table.fetchall()]


def _check_terminal_compat(terminal_obj, wire_part, project):
    """Return (is_compatible, message_or_None).

    Checks:
      1. Wire outer diameter is within the terminal's min/max range.
      2. The combined cross-section of all wires already at that terminal plus
         the new wire does not exceed the terminal's maximum.
    """
    term_part = terminal_obj.db_obj.part
    if term_part is None:
        return True, None

    dia_min = term_part.wire_size_dia_min
    dia_max = term_part.wire_size_dia_max
    cross_max = term_part.wire_size_cross_max

    wire_dia = wire_part.od_mm
    wire_cross = wire_part.size_mm2

    if dia_min is not None and wire_dia < dia_min:
        return False, f'Wire {wire_dia:.2f} mm — terminal min is {dia_min:.2f} mm'

    if dia_max is not None and wire_dia > dia_max:
        return False, f'Wire {wire_dia:.2f} mm — terminal max is {dia_max:.2f} mm'

    if cross_max is not None and wire_cross is not None:
        pos_id = terminal_obj.db_obj.position3d_id
        existing = 0.0
        for w in project.wires:
            sp = w.obj3d.start_position.db_id
            ep2 = w.obj3d.stop_position.db_id

            matched = (sp and int(sp[:-2]) == pos_id) or (ep2 and int(ep2[:-2]) == pos_id)
            if matched:
                p = w.db_obj.part
                if p is not None and p.size_mm2 is not None:
                    existing += p.size_mm2

        total = existing + wire_cross

        if total > cross_max:
            return False, (f'Combined cross-section {total:.1f} mm²'
                           f' — terminal max is {cross_max:.1f} mm²')

    return True, None


class AddWireHandler(_handler_base.HandlerBase):
    """Two-click interactive wire placement handler."""

    obj: "_wire.Wire" = None

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int = None,
                 terminal: "_terminal.Terminal" = None):
        if terminal is not None:
            compat_pns = _get_terminal_compat_pns(mainframe, terminal)

            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.WiresPage, title='Add Wire',
                table=mainframe.global_db.wires_table,
                initial_results=compat_pns)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        self._terminal_highlight = _materials.Plastic(
            _color.Color(*Config.add_object.terminal_highlight))

        self._wire_layout_highlight = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))

        self._splice_highlight = _materials.Plastic(
            _color.Color(*Config.add_object.splice_highlight))

        self._phase = 0          # 0 = waiting for start click; 1 = preview active
        self._hover_obj = None   # currently highlighted object

        # Extension mode state (first click on a wire endpoint without a layout)
        self._extension_mode = False
        self._source_wire: "_wire.Wire | None" = None
        self._source_endpoint: "str | None" = None   # 'start' or 'stop'
        self._extension_dir: "np.ndarray | None" = None    # unit vector
        self._extension_origin: "np.ndarray | None" = None  # world-space origin
        self._extension_original_pos: "np.ndarray | None" = None  # for cancel rollback

        # Temporary stop-point DB id created for the preview wire
        self._preview_stop_point_id: "int | None" = None

        # Start-click context
        self._start_point_id: "int | None" = None
        self._start_circuit_id: "int | None" = None

        # Incompatibility overlay widget (child of the 3D canvas)
        self._overlay = _IncompatOverlay(mainframe.editor3d.editor)

        if terminal is not None:
            if part_id is None:
                self._finalized = True
            else:
                self._start_from_terminal(terminal, part_id)

    def _start_from_terminal(self, terminal: "_terminal.Terminal", part_id: int):
        """Pin the preview wire's start to *terminal* and enter phase 1 directly."""
        self.part = self.mainframe.global_db.wires_table[part_id]

        start_point_id = terminal.db_obj.position3d_id
        initial_pos = terminal.obj3d.position
        self._start_circuit_id = terminal.db_obj.circuit_id
        self._start_point_id = start_point_id

        stop_db = self.ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        self._preview_stop_point_id = stop_db.db_id

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        wire_db = self.ptables.pjt_wires_table.insert(
            part_id, name, self._start_circuit_id,
            start_point_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        self.obj = _wire.Wire(self.mainframe, wire_db)
        self.obj.identify(self._preview_material)
        self._phase = 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_wire_part(self):
        """Return the global wire-part record for the current part_id, or None."""
        if self.part_id is None:
            return None

        try:
            return self.mainframe.global_db.wires_table[self.part_id]
        except (IndexError, KeyError):
            return None

    def _set_hover_obj(self, obj, material):
        if obj is not self._hover_obj:
            if self._hover_obj is not None:
                self._hover_obj.identify(None)

            if obj is not None:
                obj.identify(material)

            self._hover_obj = obj

    def _clear_hover(self):
        if self._hover_obj is not None:
            self._hover_obj.identify(None)
            self._hover_obj = None

    def _project_extension(self, world_np):
        """Project world_np onto the extension ray; never allows going backward."""
        t = float(np.dot(world_np - self._extension_origin, self._extension_dir))

        return self._extension_origin + max(0.0, t) * self._extension_dir

    def _update_preview_stop(self, world_pos):
        """Move the preview wire's stop position to world_pos."""
        if self.obj is None:
            return

        if not isinstance(world_pos, _point.Point):
            world_pos = _point.Point(*world_pos)

        stop = self.obj.obj3d.stop_position
        stop += world_pos - stop

    def _update_source_endpoint(self, world_np):
        """Live-move the source wire's endpoint to the projected ray position."""
        proj = self._project_extension(world_np)
        proj_pt = _point.Point(*proj)

        ep = (self._source_wire.obj3d.stop_position
              if self._source_endpoint == 'stop'
              else self._source_wire.obj3d.start_position)

        ep += proj_pt - ep

    def _cleanup(self):
        """Hide the overlay and unhighlight the last hovered object."""
        self._clear_hover()
        if self._overlay is not None:
            self._overlay.hide_message()

    def _destroy_overlay(self):
        if self._overlay is not None:
            self._overlay.deleteLater()
            self._overlay = None

    # ------------------------------------------------------------------
    # Public interface – hover
    # ------------------------------------------------------------------

    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        if self._phase == 0:
            self._hover_phase0(mouse_pos)
        else:
            self._hover_phase1(mouse_pos)

    def _hover_phase0(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, msg = _check_terminal_compat(picked, wire_part, project)
                if not ok:
                    self._overlay.show_message(mouse_pos, msg)
                    self._clear_hover()
                    return

            self._overlay.hide_message()
            self._set_hover_obj(picked, self._terminal_highlight)

        elif isinstance(picked, _wire_layout.WireLayout):
            self._overlay.hide_message()
            self._set_hover_obj(picked, self._wire_layout_highlight)

        elif isinstance(picked, _splice.Splice):
            self._overlay.hide_message()
            self._set_hover_obj(picked, self._splice_highlight)

        elif isinstance(picked, _wire.Wire):
            self._overlay.hide_message()
            world_np = self.camera.get_position_on_focal_plane(mouse_pos).as_numpy
            start_np = picked.obj3d.start_position.as_numpy
            stop_np = picked.obj3d.stop_position.as_numpy
            near = (float(np.linalg.norm(world_np - start_np)) < _SNAP_THRESHOLD or
                    float(np.linalg.norm(world_np - stop_np)) < _SNAP_THRESHOLD)
            if near:
                self._set_hover_obj(picked, self._wire_layout_highlight)
            else:
                self._clear_hover()

        else:
            self._overlay.hide_message()
            self._clear_hover()

    def _hover_phase1(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        world_pos_pt = self.camera.get_position_on_focal_plane(mouse_pos)

        if self._extension_mode:
            self._update_source_endpoint(world_pos_pt.as_numpy)
            self._overlay.hide_message()
            return

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if picked is self.obj:
            picked = None

        if isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, msg = _check_terminal_compat(picked, wire_part, project)
                if not ok:
                    self._overlay.show_message(mouse_pos, msg)
                    self._clear_hover()
                    self._update_preview_stop(picked.obj3d.position)
                    return

            self._overlay.hide_message()
            self._set_hover_obj(picked, self._terminal_highlight)
            self._update_preview_stop(picked.obj3d.position)

        elif isinstance(picked, _wire_layout.WireLayout):
            self._overlay.hide_message()
            end_wire, _ = _wire_layout_end_wire(picked, project, self.part_id)
            if end_wire is not None:
                self._set_hover_obj(picked, self._wire_layout_highlight)
            else:
                self._clear_hover()

            self._update_preview_stop(picked.obj3d.position)

        elif isinstance(picked, _splice.Splice):
            self._overlay.hide_message()
            self._set_hover_obj(picked, self._splice_highlight)
            self._update_preview_stop(picked.obj3d.wire_position)

        else:
            self._overlay.hide_message()
            self._clear_hover()
            self._update_preview_stop(world_pos_pt)

    # ------------------------------------------------------------------
    # Public interface – clicks
    # ------------------------------------------------------------------

    def release_capture(self):
        if self._finalized:
            return

        if self._captured_position is None:
            return

        if self._phase == 0:
            self._handle_first_click(self._captured_position)
        else:
            self._handle_second_click(self._captured_position)

    def _handle_first_click(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if isinstance(picked, _wire_layout.WireLayout):
            attached = picked.db_obj.attached_wires
            if attached:
                self.part_id = attached[0].part_id

            start_point_id = picked.db_obj.position3d_id
            initial_pos = picked.obj3d.position
            self._start_circuit_id = None

        elif isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, _ = _check_terminal_compat(picked, wire_part, project)
                if not ok:
                    return

            start_point_id = picked.db_obj.position3d_id
            initial_pos = picked.obj3d.position
            self._start_circuit_id = picked.db_obj.circuit_id

        elif isinstance(picked, _splice.Splice):
            start_point_id = picked.db_obj.branch_position3d_id
            initial_pos = picked.obj3d.wire_position
            self._start_circuit_id = None

        elif isinstance(picked, _wire.Wire):
            world_np = self.camera.get_position_on_focal_plane(mouse_pos).as_numpy
            start_np = picked.obj3d.start_position.as_numpy
            stop_np = picked.obj3d.stop_position.as_numpy
            near_start = float(np.linalg.norm(world_np - start_np)) < _SNAP_THRESHOLD
            near_stop = float(np.linalg.norm(world_np - stop_np)) < _SNAP_THRESHOLD

            if not near_start and not near_stop:
                return  # clicked mid-wire; ignore

            # Extension mode: live-move the actual wire endpoint rather than create a new wire
            self._extension_mode = True
            self._source_wire = picked
            self.part_id = picked.db_obj.part_id
            self._start_circuit_id = picked.db_obj.circuit_id

            if near_stop:
                self._source_endpoint = 'stop'
                endpoint_np = stop_np
                seg = stop_np - start_np
            else:
                self._source_endpoint = 'start'
                endpoint_np = start_np
                seg = start_np - stop_np

            seg_len = float(np.linalg.norm(seg))
            if seg_len < 1e-8:
                self._extension_mode = False
                return

            self._extension_dir = seg / seg_len
            self._extension_origin = endpoint_np.copy()
            self._extension_original_pos = endpoint_np.copy()

            self._phase = 1
            return  # no preview wire; hover moves the real wire endpoint directly

        else:
            # Free space
            world_pos = self.camera.get_position_on_focal_plane(mouse_pos)

            start_db = self.ptables.pjt_points3d_table.insert(
                float(world_pos.x), float(world_pos.y), float(world_pos.z))

            start_point_id = start_db.db_id
            initial_pos = start_db.point
            self._start_circuit_id = None

            self.part_id = self.mainframe.editor_db.editor.wires.GetSelection()

            if self.part_id is None:
                dlg = _part_search.SearchDialog(
                    self.mainframe,
                    _editor_db.WiresPage,
                    title='Add Cover',
                    table=self.mainframe.global_db.wires_table,
                )

                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.part_id = dlg.GetValue()
                else:
                    self.part_id = None

                dlg.deleteLater()

        if start_point_id is None or initial_pos is None:
            return

        if self.part_id is None:
            return

        self.part = self.mainframe.global_db.wires_table[self.part_id]

        self._start_point_id = start_point_id

        # Create the preview wire with a temporary stop point at the same location
        stop_db = self.ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        self._preview_stop_point_id = stop_db.db_id

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        wire_db = self.ptables.pjt_wires_table.insert(
            self.part_id, name, self._start_circuit_id,
            start_point_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        self.obj = _wire.Wire(self.mainframe, wire_db)
        self.obj.identify(self._preview_material)
        self._phase = 1

    def _handle_second_click(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        if self._extension_mode:
            # The source wire's endpoint has already been moved by hover(); just commit.
            self._cleanup()
            self._destroy_overlay()
            self._finalized = True
            return

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if picked is self.obj:
            picked = None

        circuit_id = self._start_circuit_id
        # Point to attach the preview stop to; None means the preview stop is already final.
        real_stop_point = None

        if isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, _ = _check_terminal_compat(picked, wire_part, project)
                if not ok:
                    return  # blocked; user already sees overlay message

            real_stop_point = picked.obj3d.position
            if circuit_id is None:
                circuit_id = picked.db_obj.circuit_id

        elif isinstance(picked, _wire_layout.WireLayout):
            end_wire, _ = _wire_layout_end_wire(picked, project, self.part_id)
            if end_wire is not None:
                real_stop_point = picked.obj3d.position
            # else: mid-wire or mismatched part — preview stop already at world pos; keep as-is

        elif isinstance(picked, _splice.Splice):
            real_stop_point = picked.obj3d.wire_position

        # else: free space — preview stop already correctly positioned by hover; no attach needed

        # Attach the real endpoint to the preview stop so mutations propagate both ways.
        # The preview wire is retained as the committed wire without recreating it.
        if real_stop_point is not None:
            real_stop_point.attach(self.obj.obj3d.stop_position)

        if circuit_id != self._start_circuit_id:
            self.obj.db_obj.circuit_id = circuit_id

        self.obj.identify(None)
        project.add_wire(self.obj)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel(self):
        if self._extension_mode and self._extension_original_pos is not None:
            # Roll back the source wire's endpoint to where it was before phase 1
            orig_pt = _point.Point(*self._extension_original_pos)

            ep = (self._source_wire.obj3d.stop_position
                  if self._source_endpoint == 'stop'
                  else self._source_wire.obj3d.start_position)

            ep += orig_pt - ep

        if self.obj is not None:
            self.obj.delete()
            self.obj = None

        self._cleanup()
        self._destroy_overlay()
