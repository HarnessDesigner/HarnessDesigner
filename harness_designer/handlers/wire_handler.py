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
from PySide6.QtWidgets import QLabel, QDialog, QMessageBox
from PySide6.QtCore import Qt
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import terminal as _terminal
from ..objects import splice as _splice
from ..objects import wire as _wire
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors

_SNAP_THRESHOLD = 5.0


class _IncompatOverlay(QLabel):
    """Floating label shown near the cursor when a terminal is incompatible."""

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(
            'background-color: rgba(180,0,0,200); color: white;'
            ' padding: 4px 6px; border-radius: 3px;')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

    @_check_types.do
    def show_message(self, mouse_pos, text):
        self.setText(text)
        self.adjustSize()
        self.move(int(mouse_pos.x) + 14, int(mouse_pos.y) + 14)
        self.show()
        self.raise_()

    @_check_types.do
    def hide_message(self):
        if self.isVisible():
            self.hide()


@_check_types.do
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


@_check_types.do
def _merge_wire_into(project, wire_obj: _wire.Wire, other_wire: _wire.Wire, other_end: str):
    """Join *wire_obj*'s own (dangling) stop end to *other_wire*'s
    dangling *other_end* ('start' or 'stop'), merging them into a single
    row -- part_id must already match (checked by the caller).

    *wire_obj*'s own current stop point becomes a permanent interior
    waypoint marking the seam (a WireLayout is dropped there), same as an
    ordinary bend; *other_wire*'s own waypoints follow, reversed first if
    joining to its start (so the merged chain still reads start->stop in
    one consistent direction), renumbered to continue. circuit_id is
    inherited from whichever of the two already had one set, not
    required to match. Both original rows are deleted; returns the new
    merged wire.
    """
    ptables = project.ptables
    mainframe = project.mainframe

    seam_point_id = int(wire_obj.obj3d.stop_position.db_id[:-2])
    own_waypoints = wire_obj.db_obj.waypoints3d
    seam_idx = len(own_waypoints)

    part_id = wire_obj.db_obj.part_id
    name = wire_obj.db_obj.name
    circuit_id = wire_obj.db_obj.circuit_id
    if circuit_id is None:
        circuit_id = other_wire.db_obj.circuit_id
    layer_id = wire_obj.db_obj.layer_id
    layer_view_point_id = wire_obj.db_obj.layer_view_position_id
    is_filler_wire = wire_obj.db_obj.is_filler_wire
    is_visible3d = wire_obj.db_obj.is_visible3d
    is_visible2d = wire_obj.db_obj.is_visible2d

    start_id_3d = int(wire_obj.obj3d.start_position.db_id[:-2])
    start_id_2d = wire_obj.db_obj.start_position2d_id

    if other_end == 'start':
        stop_id_3d = int(other_wire.obj3d.stop_position.db_id[:-2])
        stop_id_2d = other_wire.db_obj.stop_position2d_id
        other_waypoints = other_wire.db_obj.waypoints3d  # already start->stop order
        other_stop_sibling = other_wire.stop_sibling
    else:
        stop_id_3d = int(other_wire.obj3d.start_position.db_id[:-2])
        stop_id_2d = other_wire.db_obj.start_position2d_id
        other_waypoints = list(reversed(other_wire.db_obj.waypoints3d))
        other_stop_sibling = other_wire.start_sibling

    orig_start_sibling = wire_obj.start_sibling

    merged_db = ptables.pjt_wires_table.insert(
        part_id, name, circuit_id,
        start_id_3d, stop_id_3d,
        start_id_2d, stop_id_2d,
        is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire)

    for i, wp in enumerate(own_waypoints):
        wp.wire_id = merged_db.db_id
        wp.idx = i

    seam_point = ptables.pjt_points3d_table[seam_point_id]
    seam_point.wire_id = merged_db.db_id
    seam_point.idx = seam_idx

    for i, wp in enumerate(other_waypoints):
        wp.wire_id = merged_db.db_id
        wp.idx = seam_idx + 1 + i

    merged_obj = _wire.Wire(mainframe, merged_db)

    layout_db = ptables.pjt_wire_layouts_table.insert(seam_point_id)
    layout_obj = _wire_layout.WireLayout(mainframe, layout_db)
    project.add_wire_layout(layout_obj)

    if orig_start_sibling is not None:
        merged_obj.set_sibling(orig_start_sibling, 'start')
        orig_start_sibling.replace_wire(wire_obj, merged_obj)
    if other_stop_sibling is not None:
        merged_obj.set_sibling(other_stop_sibling, 'stop')
        other_stop_sibling.replace_wire(other_wire, merged_obj)

    project.add_wire(merged_obj)

    old_ids = (wire_obj.db_obj.db_id, other_wire.db_obj.db_id)
    for marker in project.wire_markers:
        if marker.db_obj.wire_id in old_ids:
            marker.db_obj.wire_id = merged_db.db_id
            marker.obj3d.rebind_wire(merged_db)

    for w in (wire_obj, other_wire):
        if mainframe.get_selected() is w:
            w.set_selected(False)
        w.delete()

    return merged_obj


@_check_types.do
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


@_check_types.do
def _check_terminal_compat(terminal_obj, wire_part):
    """Return (is_compatible, message_or_None).

    Checks:
      1. Wire outer diameter is within the terminal's min/max range.
      2. The combined cross-section of all wires already at that terminal plus
         the new wire does not exceed the terminal's maximum.
    """
    term_part = terminal_obj.db_obj.part
    if term_part is None:
        return True, None

    awg_min = term_part.wire_size_awg_min
    awg_max = term_part.wire_size_awg_max

    wire_awg = wire_part.size_awg

    cross_max = term_part.wire_size_cross_max
    wire_cross = wire_part.size_mm2

    if awg_min is not None and wire_awg < awg_min:
        return False, f'Wire {wire_awg} AWG — terminal min is {awg_min} AWG'

    if awg_max is not None and wire_awg > awg_max:
        return False, f'Wire {wire_awg} AWG — terminal max is {wire_awg} AWG'

    if cross_max is not None and wire_cross is not None:
        # For the hover-preview message only -- terminal_obj.add_wire
        # (called once the attach is actually committed) makes this exact
        # same check itself against its own .wires list, which is the
        # real enforcement; this is purely so the incompatibility overlay
        # can show a number before the user commits to anything.
        existing = sum(
            w.db_obj.part.size_mm2 for w in terminal_obj.wires
            if w.db_obj.part is not None and w.db_obj.part.size_mm2 is not None)

        total = existing + wire_cross

        if total > cross_max:
            return False, (f'Combined cross-section {total:.1f} mm²'
                           f' — terminal max is {cross_max:.1f} mm²')

    return True, None


class AddWireHandler(_handler_base.HandlerBase):
    """Two-click interactive wire placement handler."""

    obj: _wire.Wire = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", part_id: int = None,
                 terminal: _terminal.Terminal = None):
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
        self._source_wire: _wire.Wire | None = None
        self._source_endpoint: str | None = None   # 'start' or 'stop'
        self._extension_dir: np.ndarray | None = None    # unit vector
        self._extension_origin: np.ndarray | None = None  # world-space origin
        self._extension_original_pos: np.ndarray | None = None  # for cancel rollback

        # Temporary stop-point DB id created for the preview wire
        self._preview_stop_point_id: int | None = None

        # Start-click context
        self._start_point_id: int | None = None
        self._start_circuit_id: int | None = None

        # WireLayouts dropped this session by _commit_waypoint() (one per
        # user-confirmed free-space click) -- rolled back by cancel(), and
        # the last one popped by finalize_at_last_point() if discarding
        # the in-progress segment leaves it marking a terminus instead of
        # a joint. Never includes terminal.add_wire's own back/cavity
        # layouts -- those live for as long as self.obj itself does,
        # cleaned up as part of deleting the wire row (see PJTWire.delete),
        # not tracked separately here.
        self._committed_layouts: list = []

        # True once at least one _commit_waypoint() (a real, user-confirmed
        # free-space click) has landed -- distinct from a fresh self.obj
        # already having waypoints from terminal.add_wire's own routing.
        # finalize_at_last_point() uses this to decide between "keep what's
        # committed" and "the user never confirmed anything, cancel it all".
        self._has_committed_waypoint = False

        # Incompatibility overlay widget (child of the 3D canvas)
        self._overlay = _IncompatOverlay(mainframe.editor3d.editor)

        if terminal is not None:
            if part_id is None:
                self._finalized = True
            else:
                self._start_from_terminal(terminal, part_id)

    @_check_types.do
    def _start_from_terminal(self, terminal: _terminal.Terminal, part_id: int):
        """Pin the preview wire's start to *terminal* and enter phase 1 directly."""
        self.part = self.mainframe.global_db.wires_table[part_id]

        # Unlike the hover/first-click terminal-start paths (_hover_phase0,
        # _handle_first_click), nothing has checked compatibility yet here --
        # the part-search dialog above is pre-filtered by diameter but does
        # not enforce it, and diameter compatibility doesn't imply
        # cross-section compatibility. Check before creating anything.
        ok, msg = _check_terminal_compat(terminal, self.part)
        if not ok:
            msg += '\n\nDo you want to use this wire?'
            button = QMessageBox.question(self.mainframe, 'Incompatible Wire', msg)
            if button == QMessageBox.StandardButton.No:
                self._finalized = True
                return

        self._start_circuit_id = terminal.db_obj.circuit_id

        # Placeholder start -- terminal.add_wire below overwrites it with
        # the terminal's own true attach point and extends this same
        # wire's own waypoint list through the terminal's back point (and,
        # if seated in a cavity, the cavity's own wire-position point too)
        # -- see objects.terminal.Terminal.add_wire. No separate stub
        # wires/rows are created for that routing any more.
        placeholder_id = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

        initial_pos = terminal.db_obj.attach_position3d
        stop_db = self.ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        self._preview_stop_point_id = stop_db.db_id

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        wire_db = self.ptables.pjt_wires_table.insert(
            part_id, name, self._start_circuit_id,
            placeholder_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        self.obj = _wire.Wire(self.mainframe, wire_db)
        # self.obj.identify(self._preview_material)

        if not terminal.add_wire(self.obj, 'start'):
            # Belt-and-suspenders: the compat check above should already
            # prevent this, but never leave a wire row with its start still
            # pointing at the placeholder about to be deleted -- that's
            # exactly what produced a wire rendering at world origin (and
            # crashing on the next project reload with an orphaned FK)
            # before this check existed. PJTWire.delete() never touches
            # start/stop points (they're owned by whatever they're attached
            # to, not the wire), so the placeholder and preview stop point
            # need cleaning up explicitly.
            self.obj.delete()
            self.obj = None
            self.ptables.pjt_points3d_table[placeholder_id].delete()
            self.ptables.pjt_points3d_table[stop_db.db_id].delete()
            QMessageBox.warning(
                self.mainframe, 'Incompatible Wire',
                'This wire is no longer compatible with the terminal.')
            self._finalized = True
            return

        self.ptables.pjt_points3d_table[placeholder_id].delete()

        self._phase = 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_check_types.do
    def _get_wire_part(self):
        """Return the global wire-part record for the current part_id, or None."""
        if self.part_id is None:
            return None

        try:
            return self.mainframe.global_db.wires_table[self.part_id]
        except (IndexError, KeyError):
            return None

    @_check_types.do
    def _set_hover_obj(self, obj, material):
        if obj is not self._hover_obj:
            if self._hover_obj is not None:
                self._hover_obj.identify(None)

            if obj is not None:
                obj.identify(material)

            self._hover_obj = obj

    @_check_types.do
    def _clear_hover(self):
        if self._hover_obj is not None:
            self._hover_obj.identify(None)
            self._hover_obj = None

    @_check_types.do
    def _project_extension(self, world_np):
        """Project world_np onto the extension ray; never allows going backward."""
        t = float(np.dot(world_np - self._extension_origin, self._extension_dir))

        return self._extension_origin + max(0.0, t) * self._extension_dir

    @_check_types.do
    def _update_preview_stop(self, world_pos):
        """Move the preview wire's stop position to world_pos."""
        if self.obj is None:
            return

        if not isinstance(world_pos, _point.Point):
            world_pos = _point.Point(*world_pos)

        stop = self.obj.obj3d.stop_position
        stop += world_pos - stop

        # Wire._update_position (bound to this point) only marks the
        # wire's geometry stale for the next render -- unlike most other
        # objects' _update_position, it doesn't request a repaint itself
        # (see objects.objects3d.wire.Wire._update_position), so without
        # this the preview only catches up whenever something else
        # happens to trigger a repaint (zoom, camera move).
        self.mainframe.editor3d.Refresh(False)

    @_check_types.do
    def _update_source_endpoint(self, world_np):
        """Live-move the source wire's endpoint to the projected ray position."""
        proj = self._project_extension(world_np)
        proj_pt = _point.Point(*proj)

        ep = (self._source_wire.obj3d.stop_position
              if self._source_endpoint == 'stop'
              else self._source_wire.obj3d.start_position)

        ep += proj_pt - ep

        # See _update_preview_stop -- same deferred-repaint gap.
        self.mainframe.editor3d.Refresh(False)

    @_check_types.do
    def _cleanup(self):
        """Hide the overlay and unhighlight the last hovered object."""
        self._clear_hover()
        if self._overlay is not None:
            self._overlay.hide_message()

    @_check_types.do
    def _destroy_overlay(self):
        if self._overlay is not None:
            self._overlay.deleteLater()
            self._overlay = None

    # ------------------------------------------------------------------
    # Public interface – hover
    # ------------------------------------------------------------------

    @_check_types.do
    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        if self._phase == 0:
            self._hover_phase0(mouse_pos)
        else:
            self._hover_phase1(mouse_pos)

    @_check_types.do
    def _hover_phase0(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, msg = _check_terminal_compat(picked, wire_part)
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

    @_check_types.do
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
                ok, msg = _check_terminal_compat(picked, wire_part)
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

    @_check_types.do
    def release_capture(self):
        if self._finalized:
            return

        if self._captured_position is None:
            return

        if self._phase == 0:
            self._handle_first_click(self._captured_position)
        else:
            self._handle_second_click(self._captured_position)

    @_check_types.do
    def _handle_first_click(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        # Set below only when picked is a Terminal -- terminal.add_wire is
        # called on it once self.obj exists, at the end of this method,
        # since it needs the real wire object (not just a point id) to
        # attach the start end to and extend with its own routing
        # waypoints. None everywhere else.
        start_terminal = None

        if isinstance(picked, _wire_layout.WireLayout):
            attached = picked.db_obj.attached_wires
            if attached:
                self.part_id = attached[0].part_id

            start_point_id = picked.db_obj.position3d_id
            initial_pos = picked.obj3d.position
            self._start_circuit_id = None

        elif isinstance(picked, _terminal.Terminal):
            # A wire part must already be chosen to route the terminal's
            # own back/cavity waypoints -- unlike free space, there's no
            # part-search fallback for a terminal-first click, so bail
            # before creating anything (matches the part_id is None guard
            # below).
            if wire_part is None:
                return

            ok, msg = _check_terminal_compat(picked, wire_part)
            if not ok:
                msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(self.mainframe, 'Incompatible Wire', msg)
                if button == QMessageBox.StandardButton.No:
                    return

            self._start_circuit_id = picked.db_obj.circuit_id
            start_terminal = picked

            # Placeholder -- terminal.add_wire (below, once self.obj
            # exists) overwrites this with the terminal's own true attach
            # point and extends self.obj's own waypoint list through its
            # back/cavity points. No separate stub wires/rows.
            start_db = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            start_point_id = start_db.db_id
            initial_pos = picked.db_obj.attach_position3d

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
        # self.obj.identify(self._preview_material)
        self._phase = 1

        if start_terminal is not None:
            start_terminal.add_wire(self.obj, 'start')
            self.ptables.pjt_points3d_table[start_point_id].delete()

    @_check_types.do
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

        if isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, msg = _check_terminal_compat(picked, wire_part)
                if not ok:
                    msg += '\n\nDo you want to use this wire?'
                    button = QMessageBox.question(self.mainframe, 'Incompatible Wire', msg)
                    if button == QMessageBox.StandardButton.No:
                        return

            if circuit_id is None:
                circuit_id = picked.db_obj.circuit_id

            # Discard the temporary preview stop point -- terminal.add_wire
            # overwrites stop_position3d_id with the terminal's own true
            # attach point and extends this same wire's own waypoint list
            # through its back (and, if seated in a cavity, the cavity's
            # own wire-position) point.
            stale_stop_id = int(self.obj.obj3d.stop_position.db_id[:-2])
            picked.add_wire(self.obj, 'stop')
            self.ptables.pjt_points3d_table[stale_stop_id].delete()

        elif isinstance(picked, _wire_layout.WireLayout):
            end_wire, _ = _wire_layout_end_wire(picked, project, self.part_id)
            if end_wire is not None:
                # picked.obj3d.position is the same live, singleton Point
                # object end_wire's own endpoint already uses (Point
                # instances are singletons keyed by db_id -- see
                # database.project_db.pjt_point3d.PJTPoint3D's docstring),
                # so pointing this wire's own stop at it directly gives
                # the same live sharing a .attach() delegation would, with
                # no delegation machinery needed.
                stale_stop_id = int(self.obj.obj3d.stop_position.db_id[:-2])
                self.obj.obj3d.set_stop_position(picked.obj3d.position)
                self.obj.db_obj.stop_position3d_id = picked.db_obj.position3d_id
                self.ptables.pjt_points3d_table[stale_stop_id].delete()
            # else: mid-wire or mismatched part — preview stop already at world pos; keep as-is

        elif isinstance(picked, _splice.Splice):
            stale_stop_id = int(self.obj.obj3d.stop_position.db_id[:-2])
            self.obj.obj3d.set_stop_position(picked.obj3d.wire_position)
            self.obj.db_obj.stop_position3d_id = picked.db_obj.branch_position3d_id
            self.ptables.pjt_points3d_table[stale_stop_id].delete()

            self.obj.db_obj.stop_position2d_id = picked.db_obj.position2d_id
            self.obj.obj2d.set_stop_position(picked.db_obj.position2d)

            picked.add_wire(self.obj)
            self.obj.set_sibling(picked, 'stop')

        elif isinstance(picked, _wire.Wire):
            # Joining this (still-dangling) wire's stop to another,
            # separately-drawn dangling wire's endpoint -- they're the
            # same physical wire once connected, so they merge into one
            # row (with a WireLayout at the seam) rather than staying
            # linked; see _merge_wire_into.
            world_np = self.camera.get_position_on_focal_plane(mouse_pos).as_numpy
            start_np = picked.obj3d.start_position.as_numpy
            stop_np = picked.obj3d.stop_position.as_numpy
            near_start = float(np.linalg.norm(world_np - start_np)) < _SNAP_THRESHOLD
            near_stop = float(np.linalg.norm(world_np - stop_np)) < _SNAP_THRESHOLD

            if not near_start and not near_stop:
                self._commit_waypoint()
                return

            if picked.db_obj.part_id != self.obj.db_obj.part_id:
                self._overlay.show_message(
                    mouse_pos, 'Different wire part — cannot join')
                return

            other_end = 'start' if near_start else 'stop'
            merged = _merge_wire_into(project, self.obj, picked, other_end)
            self.obj = merged

            self.obj.identify(None)
            self._cleanup()
            self._destroy_overlay()
            self._finalized = True
            return

        else:
            # Free space — not the end of the wire, just an intermediate
            # waypoint. Commit the current segment where hover already
            # tracked it, drop a WireLayout there, and keep going instead
            # of finalizing — the wire only ends by hitting one of the
            # attach targets above, or via right-click/Escape.
            self._commit_waypoint()
            return

        if circuit_id != self._start_circuit_id:
            self.obj.db_obj.circuit_id = circuit_id

        self.obj.identify(None)
        project.add_wire(self.obj)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    @_check_types.do
    def _commit_waypoint(self) -> None:
        """
        Commit the current live preview stop position as a permanent
        interior waypoint on this *same* wire (no new ``pjt_wires`` row --
        see handlers.wire_layout_handler._create_wire_layout_on_wire, the
        same operation performed inline here since the wire is still
        being drawn), drop a :class:`WireLayout` there, and continue the
        preview from a fresh stop point past it.  Called when a mid-
        placement click lands in free space instead of on an attachable
        target; stays in phase 1 (loops back for the next click) rather
        than finalizing.
        """
        project = self.mainframe.project

        self._has_committed_waypoint = True

        stop_point_id = self._preview_stop_point_id
        stop_pos = self.obj.obj3d.stop_position

        existing = self.obj.db_obj.waypoints3d
        new_idx = len(existing)

        point = self.ptables.pjt_points3d_table[stop_point_id]
        point.wire_id = self.obj.db_obj.db_id
        point.idx = new_idx

        layout_db = self.ptables.pjt_wire_layouts_table.insert(stop_point_id)
        layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
        project.add_wire_layout(layout_obj)
        self._committed_layouts.append(layout_obj)

        new_stop_db = self.ptables.pjt_points3d_table.insert(
            float(stop_pos.x), float(stop_pos.y), float(stop_pos.z))
        self._preview_stop_point_id = new_stop_db.db_id

        # The just-committed point becomes a permanent interior waypoint;
        # the wire's own stop moves on to the fresh point, continuing the
        # live preview -- same wire object and row throughout.
        self.obj.db_obj.stop_position3d_id = new_stop_db.db_id
        self.obj.obj3d.set_stop_position(new_stop_db.point)
        self.obj.obj3d.refresh_waypoints()

    # ------------------------------------------------------------------
    # Finishing early / cancellation
    # ------------------------------------------------------------------

    @_check_types.do
    def finalize_at_last_point(self) -> None:
        """
        Right-click: end the wire at the last confirmed point, discarding
        the current in-progress, not-yet-committed segment rather than
        tracking the mouse further or finalizing at the cursor.

        If the user has confirmed at least one real waypoint (a free-space
        left-click, via _commit_waypoint()), that waypoint is promoted
        back to being this wire's own true stop (undoing the "continue
        past it" part of _commit_waypoint, which had already moved the
        stop on to the now-discarded in-progress point) and everything
        else committed before it is left in place as the finished wire.
        If not -- e.g. the wire was started on a terminal and
        right-clicked immediately, with only its own back/cavity routing
        waypoints in place and no destination ever confirmed -- there's
        nothing meaningful to finish, so the whole thing is cancelled
        instead of leaving a routing-only fragment behind.
        """
        if self._finalized or self._phase == 0:
            return

        if self._extension_mode:
            # Nothing uncommitted to discard -- the real wire's endpoint
            # simply stops wherever hover last left it.
            self._cleanup()
            self._destroy_overlay()
            self._finalized = True
            return

        if not self._has_committed_waypoint:
            self.cancel()
            self._finalized = True
            return

        # Discard the in-progress (never-confirmed) stop point and
        # promote the last confirmed waypoint back to being this wire's
        # own true stop -- see WireTypeMixin._segments()/waypoints3d:
        # ordered by idx, so [-1] is the most recently committed one.
        stale_stop_id = int(self.obj.obj3d.stop_position.db_id[:-2])
        last_waypoint = self.obj.db_obj.waypoints3d[-1]
        last_point = last_waypoint.point

        last_waypoint.wire_id = None
        last_waypoint.idx = None

        self.obj.db_obj.stop_position3d_id = last_waypoint.db_id
        self.obj.obj3d.set_stop_position(last_point)

        self.ptables.pjt_points3d_table[stale_stop_id].delete()

        # _commit_waypoint() eagerly drops a WireLayout at every free-space
        # click, on the assumption the run continues past it. Discarding
        # the in-progress segment above can leave the very last one of
        # those marking what's now this wire's own terminus instead of a
        # joint between two sections -- remove it in that case; the wire
        # still ends at the exact same point, just without a layout
        # marker rendered there.
        if self._committed_layouts:
            last_layout = self._committed_layouts[-1]
            if len(last_layout.db_obj.attached_wires) < 2:
                last_layout.delete()
                self._committed_layouts.pop()

        self.obj.obj3d.refresh_waypoints()
        self.mainframe.project.add_wire(self.obj)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    @_check_types.do
    def cancel(self):
        if self._extension_mode and self._extension_original_pos is not None:
            # Roll back the source wire's endpoint to where it was before phase 1
            orig_pt = _point.Point(*self._extension_original_pos)

            ep = (self._source_wire.obj3d.stop_position
                  if self._source_endpoint == 'stop'
                  else self._source_wire.obj3d.start_position)

            ep += orig_pt - ep

        # Every committed WireLayout sits on one of self.obj's own
        # waypoints, so deleting the wire below would clean these up too
        # (see PJTWire.delete) -- deleted explicitly here anyway for
        # symmetry with finalize_at_last_point's own bookkeeping of this
        # same list, and so the list is always left empty either way.
        for layout_obj in reversed(self._committed_layouts):
            layout_obj.delete()
        self._committed_layouts = []

        if self.obj is not None:
            self.obj.delete()
            self.obj = None

        self._cleanup()
        self._destroy_overlay()
