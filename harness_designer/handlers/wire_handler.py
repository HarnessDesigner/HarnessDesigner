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
from PySide6.QtWidgets import QDialog, QMessageBox
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from . import wire_snap as _wire_snap
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


@_check_types.do
def _wire_layout_end_wire(wire_layout_obj, project, part_id: bytes):
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
        if start_str and start_str[:-2] == layout_pos_id:
            matching.append((w, 'start'))

        elif stop_str and stop_str[:-2] == layout_pos_id:
            matching.append((w, 'stop'))

    if len(matching) == 1:
        w, ep = matching[0]
        if w.db_obj.part_id == part_id:
            return w, ep

    return None, None


@_check_types.do
def merge_wire_into(project, wire_obj: _wire.Wire, other_wire: _wire.Wire, other_end: str,
                     own_end: str = 'stop'):
    """Join *wire_obj*'s own dangling *own_end* ('start' or 'stop';
    default 'stop' -- the two-click preview flow's own always-growing end,
    the only case that existed before this took an own_end parameter) to
    *other_wire*'s dangling *other_end*, merging them into a single row --
    part_id must already match (checked by the caller). Also the commit
    path for a snapped wire-to-wire endpoint drag (see
    handlers.wire_snap.commit_snap) -- own_end there is whichever end was
    actually dragged, which can be either one.

    *wire_obj*'s own current *own_end* point becomes a permanent interior
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

    if own_end == 'start':
        # Mirror image of the 'stop' case below: wire_obj's own far/outer
        # end is now its stop (own_end is the seam), so its own waypoints
        # need reversing to still walk outer-end-toward-seam in the
        # merged wire's own start->stop order.
        seam_point_id = wire_obj.obj3d.start_position.db_id[:-2]
        own_waypoints = list(reversed(wire_obj.db_obj.waypoints3d))
        start_id_3d = wire_obj.obj3d.stop_position.db_id[:-2]
        start_id_2d = wire_obj.db_obj.stop_position2d_id
        orig_start_sibling = wire_obj.stop_sibling
    else:
        seam_point_id = wire_obj.obj3d.stop_position.db_id[:-2]
        own_waypoints = wire_obj.db_obj.waypoints3d
        start_id_3d = wire_obj.obj3d.start_position.db_id[:-2]
        start_id_2d = wire_obj.db_obj.start_position2d_id
        orig_start_sibling = wire_obj.start_sibling

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

    if other_end == 'start':
        stop_id_3d = other_wire.obj3d.stop_position.db_id[:-2]
        stop_id_2d = other_wire.db_obj.stop_position2d_id
        other_waypoints = other_wire.db_obj.waypoints3d  # already start->stop order
        other_stop_sibling = other_wire.stop_sibling
    else:
        stop_id_3d = other_wire.obj3d.start_position.db_id[:-2]
        stop_id_2d = other_wire.db_obj.start_position2d_id
        other_waypoints = list(reversed(other_wire.db_obj.waypoints3d))
        other_stop_sibling = other_wire.start_sibling

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
def _get_splice_compat_pns(mainframe, splice_obj):
    """Return wire part numbers whose outer diameter fits *splice_obj*'s crimp range."""
    splice_part = splice_obj.db_obj.part
    if splice_part is None:
        return []

    dia_min = splice_part.wire_size_dia_min
    dia_max = splice_part.wire_size_dia_max

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
def _pick_free_end(mainframe, wire_obj: _wire.Wire, click_pos: _point.Point = None) -> str | None:
    """Return ``'start'``/``'stop'`` -- whichever end of *wire_obj* is free
    to extend/add onto (see ``objects.objects3d.wire.WireMenu``'s Extend
    Wire/Add to Wire actions) -- or ``None`` if both ends are anchored to a
    terminal/cavity (those menu actions are disabled in that case).

    Exactly one free end wins outright; with both free, whichever is
    closer to *click_pos* (where the context menu was opened) wins, using
    the same closest-point-on-path technique
    ``gl.canvas3d.dragging.plan_wire_drag``/``PathDragObject`` already use
    to decide "which end did the user mean" elsewhere.
    """
    from ..gl.canvas3d import dragging as _dragging  # NOQA -- avoid a cycle at import time

    project = mainframe.project
    start_anchored, stop_anchored = _dragging.wire_end_anchors(project, wire_obj)

    if start_anchored and stop_anchored:
        return None

    if start_anchored:
        return 'stop'

    if stop_anchored:
        return 'start'

    obj3d = wire_obj.obj3d

    if click_pos is None:
        return 'stop'

    closest_point, _angle, _seg_idx = obj3d.get_closest_point(click_pos)
    if closest_point is None:
        return 'stop'

    start_dist = float(np.linalg.norm(closest_point.as_numpy - obj3d.start_position.as_numpy))
    stop_dist = float(np.linalg.norm(closest_point.as_numpy - obj3d.stop_position.as_numpy))

    return 'start' if start_dist <= stop_dist else 'stop'


class AddWireHandler(_handler_base.HandlerBase):
    """Two-click interactive wire placement handler."""

    obj: _wire.Wire = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", part_id: bytes | None = None,
                 terminal: _terminal.Terminal = None, splice: _splice.Splice = None,
                 extend_wire: tuple = None, add_to_wire: tuple = None):
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

        elif splice is not None:
            compat_pns = _get_splice_compat_pns(mainframe, splice)

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

        # Incompatibility/capacity-warning overlay widget (child of the 3D canvas)
        self._overlay = _wire_snap.SnapOverlay(mainframe.editor3d.editor)

        # Invisible snap-sphere probes (see handlers.wire_snap) -- built
        # lazily by _ensure_snap_probes() once the wire part is known
        # (rebuilt if it later changes), torn down by _cleanup().
        self._snap_probes: _wire_snap.SnapProbeSet | None = None
        self._snap_probes_part_id: bytes | None = None

        # Extension-mode snap state (see _hover_phase1/_handle_second_click's
        # own extension-mode branches) -- mirrors dragging.WireDragObject's
        # snapped_kind/snapped_target shape, just for the source wire's own
        # endpoint instead of a drag object's moving point.
        self._extension_snap_kind: str | None = None
        self._extension_snap_target = None

        # Which end of self.obj the live preview grows from -- every entry
        # point except _start_add_to_wire leaves this at the long-standing
        # 'stop' default (matches every phase-1 method's own historical
        # stop-only assumption exactly). Only _start_add_to_wire (continuing
        # an already-placed wire from its own free end, which may be
        # 'start') ever sets this to 'start'.
        self._growing_end: str = 'stop'

        # True only for _start_add_to_wire -- self.obj there is a real,
        # already-registered, already-placed wire being continued, not a
        # fresh throwaway preview row. Guards two things that assume the
        # opposite everywhere else: project.add_wire(self.obj) on a
        # successful finalize (would double-count project.obj_count for an
        # already-registered wire) and cancel()'s self.obj.delete() (would
        # destroy the real pre-existing wire instead of just undoing this
        # session's own additions).
        self._preexisting_wire: bool = False

        # How many waypoints _commit_growing_point_as_waypoint() has tagged
        # this session (including _start_add_to_wire's own initial one) --
        # an independent counter rather than len(self._committed_layouts),
        # since a committed layout that ends up with 2+ attached wires is
        # deliberately NOT popped from that list (see
        # _promote_last_committed) and would otherwise make a "loop until
        # _committed_layouts is empty" cancel() rollback loop forever.
        self._session_waypoint_count: int = 0

        if terminal is not None:
            if part_id is None:
                self._finalized = True
            else:
                self._start_from_terminal(terminal, part_id)
        elif splice is not None:
            if part_id is None:
                self._finalized = True
            else:
                self._start_from_splice(splice, part_id)
        elif extend_wire is not None:
            self._start_extend_from_wire(*extend_wire)
        elif add_to_wire is not None:
            self._start_add_to_wire(*add_to_wire)

    @_check_types.do
    def _start_from_splice(self, splice: _splice.Splice, part_id: bytes):
        """Pin the preview wire's start to *splice*'s own branch point and
        enter phase 1 directly."""
        self.part = self.mainframe.global_db.wires_table[part_id]

        # Same reasoning as _start_from_terminal: the part-search dialog
        # above is pre-filtered by diameter but doesn't enforce it, and
        # diameter compatibility doesn't imply cross-section compatibility.
        ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(splice, self.part)
        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
            if button == QMessageBox.StandardButton.No:
                self._finalized = True
                return

        self._start_circuit_id = None

        # The splice's own branch point is reused directly as this wire's
        # start -- never cloned (see handlers.wire_snap.commit_snap's
        # splice branch: every branch wire on a splice shares the exact
        # same branch_position3d_id, unlike a terminal's own back-routing
        # point). No WireLayout at start either -- the splice's own mesh
        # already marks the junction, matching objects.splice.Splice.
        # add_wire's own docstring.
        start_point_id = splice.db_obj.branch_position3d_id
        initial_pos = splice.obj3d.wire_position

        stop_db = self.ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        self._preview_stop_point_id = stop_db.db_id

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        wire_db = self.ptables.pjt_wires_table.insert(
            part_id, name, self._start_circuit_id,
            start_point_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        self.obj = _wire.Wire(self.mainframe, wire_db)

        splice.add_wire(self.obj)
        self.obj.set_sibling(splice, 'start')

        self._phase = 1

    @_check_types.do
    def _start_from_terminal(self, terminal: _terminal.Terminal, part_id: bytes):
        """Pin the preview wire's start to *terminal* and enter phase 1 directly."""
        self.part = self.mainframe.global_db.wires_table[part_id]

        # Unlike the hover/first-click terminal-start paths (_hover_phase0,
        # _handle_first_click), nothing has checked compatibility yet here --
        # the part-search dialog above is pre-filtered by diameter but does
        # not enforce it, and diameter compatibility doesn't imply
        # cross-section compatibility. Check before creating anything.
        ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(terminal, self.part)
        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
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

        # Terminal.add_wire always performs the attachment now -- it never
        # refuses based on combined cross-section (see its own docstring),
        # the only thing that used to make this return False.
        terminal.add_wire(self.obj, 'start')
        self.ptables.pjt_points3d_table[placeholder_id].delete()

        self._phase = 1

    @_check_types.do
    def _start_extend_from_wire(self, wire_obj: _wire.Wire, end: str):
        """Enter extension mode directly on *wire_obj*'s own *end* -- the
        same mechanic _handle_first_click's own Wire-branch already builds
        when the user clicks near an existing wire's end during free-draw,
        just entered straight from the wire's own context menu instead of
        requiring a fresh click to find it. No preview wire is created --
        hover moves wire_obj's own real endpoint directly, same as the
        free-draw path (see _hover_phase1/_handle_second_click's own
        ``if self._extension_mode:`` branches).
        """
        obj3d = wire_obj.obj3d
        start_np = obj3d.start_position.as_numpy
        stop_np = obj3d.stop_position.as_numpy

        self._extension_mode = True
        self._source_wire = wire_obj
        self.part_id = wire_obj.db_obj.part_id
        self._start_circuit_id = wire_obj.db_obj.circuit_id

        if end == 'stop':
            self._source_endpoint = 'stop'
            endpoint_np = stop_np
            seg = stop_np - start_np
        else:
            self._source_endpoint = 'start'
            endpoint_np = start_np
            seg = start_np - stop_np

        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-8:
            # Degenerate (zero-length) wire -- nothing to extend in any
            # meaningful direction; matches the free-draw path's own guard.
            self._extension_mode = False
            self._finalized = True
            return

        self._extension_dir = seg / seg_len
        self._extension_origin = endpoint_np.copy()
        self._extension_original_pos = endpoint_np.copy()

        self._phase = 1

    @_check_types.do
    def _start_add_to_wire(self, wire_obj: _wire.Wire, end: str):
        """Continue *wire_obj* from its own free *end* -- tags that end as
        a permanent interior waypoint (own WireLayout) via
        _commit_growing_point_as_waypoint, then continues the live preview
        from a fresh point there, exactly like a free-space click
        mid-placement (_commit_waypoint) except entered directly from the
        wire's own context menu instead of requiring an active placement
        session already in progress.

        Unlike every other entry point, self.obj here is a real,
        already-placed, already-registered wire -- see self._preexisting_wire
        (guards project.add_wire double-registration on finalize and
        self.obj.delete() on cancel) and self._growing_end (may be 'start',
        unlike every other entry point's fixed 'stop').
        """
        self.part_id = wire_obj.db_obj.part_id
        self.part = self.mainframe.global_db.wires_table[self.part_id]

        self.obj = wire_obj
        self._start_circuit_id = wire_obj.db_obj.circuit_id
        self._growing_end = end
        self._preexisting_wire = True

        if end == 'stop':
            self._preview_stop_point_id = wire_obj.db_obj.stop_position3d_id
        else:
            self._preview_stop_point_id = wire_obj.db_obj.start_position3d_id

        self._commit_growing_point_as_waypoint()

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
    def _ensure_snap_probes(self) -> None:
        """(Re)build this session's invisible snap probes once the wire
        part is known -- a probe at every terminal's own attach point and
        every other open, same-part wire end (see handlers.wire_snap) --
        so hover picking finds a generous sphere instead of needing an
        exact hit on a terminal's tiny mesh or a marker-less dangling end.
        Rebuilt if the part changes; no-op otherwise.
        """
        wire_part = self._get_wire_part()
        if wire_part is None:
            return

        if self._snap_probes is not None and self._snap_probes_part_id == wire_part.db_id:
            return

        if self._snap_probes is not None:
            self._snap_probes.close()

        # Extension mode has no preview wire (self.obj stays None for its
        # entire lifetime) -- the wire actually being drawn/extended right
        # now is self._source_wire instead. Excluding whichever one is
        # live is essential, not just tidy: without it, the wire's own
        # other (still-dangling) end -- or even the very end being
        # dragged, at its pre-drag position -- gets its own probe, and
        # snapping onto it would try to merge the wire into itself.
        exclude_wire = self.obj if self.obj is not None else self._source_wire

        self._snap_probes = _wire_snap.SnapProbeSet(
            self.mainframe, wire_part, exclude_wire=exclude_wire)
        self._snap_probes_part_id = wire_part.db_id

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

    @property
    @_check_types.do
    def _growing_point(self) -> _point.Point:
        """The live Point self.obj's preview is currently growing from --
        stop_position for every entry point except _start_add_to_wire,
        which may set self._growing_end to 'start' instead (continuing an
        already-placed wire from its own free start end)."""
        if self._growing_end == 'stop':
            return self.obj.obj3d.stop_position

        return self.obj.obj3d.start_position

    @_check_types.do
    def _set_growing_position3d_id(self, point_id) -> None:
        if self._growing_end == 'stop':
            self.obj.db_obj.stop_position3d_id = point_id
        else:
            self.obj.db_obj.start_position3d_id = point_id

    @_check_types.do
    def _set_growing_position2d_id(self, point_id) -> None:
        if self._growing_end == 'stop':
            self.obj.db_obj.stop_position2d_id = point_id
        else:
            self.obj.db_obj.start_position2d_id = point_id

    @_check_types.do
    def _set_growing_obj3d_position(self, point: _point.Point) -> None:
        if self._growing_end == 'stop':
            self.obj.obj3d.set_stop_position(point)
        else:
            self.obj.obj3d.set_start_position(point)

    @_check_types.do
    def _set_growing_objschematic_position(self, point: _point.Point) -> None:
        if self._growing_end == 'stop':
            self.obj.objschematic.set_stop_position(point)
        else:
            self.obj.objschematic.set_start_position(point)

    @_check_types.do
    def _update_preview_stop(self, world_pos):
        """Move the preview wire's growing end to world_pos (stop_position
        for every entry point except _start_add_to_wire -- see
        self._growing_end/_growing_point)."""
        if self.obj is None:
            return

        if not isinstance(world_pos, _point.Point):
            world_pos = _point.Point(*world_pos)

        growing = self._growing_point
        growing += world_pos - growing

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
        """Hide the overlay, unhighlight the last hovered object, and tear
        down this session's snap probes -- called on every cancel/finalize
        path (see _ensure_snap_probes)."""
        self._clear_hover()
        if self._overlay is not None:
            self._overlay.hide_message()

        if self._snap_probes is not None:
            self._snap_probes.close()
            self._snap_probes = None
            self._snap_probes_part_id = None

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

        self._ensure_snap_probes()

        with self.mainframe.editor3d.context:
            if self._phase == 0:
                self._hover_phase0(mouse_pos)
            else:
                self._hover_phase1(mouse_pos)

    @_check_types.do
    def _hover_phase0(self, mouse_pos):
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view,
            self.camera, self._get_view_object)

        picked = _wire_snap.resolve_picked(picked)

        if isinstance(picked, _terminal.Terminal):
            warning_msg = None
            if wire_part is not None:
                ok, block_msg, warning_msg = _wire_snap.check_terminal_compat(picked, wire_part)
                if not ok:
                    self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                    self._clear_hover()
                    return

            if warning_msg:
                self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
            else:
                self._overlay.hide_message()

            self._set_hover_obj(picked, self._terminal_highlight)

        elif isinstance(picked, _splice.Splice):
            ok, block_msg, warning_msg = _wire_snap.check_splice_compat(picked, wire_part) \
                if wire_part is not None else (True, None, None)
            if not ok:
                self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                self._clear_hover()
                return

            if warning_msg:
                self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
            else:
                self._overlay.hide_message()

            self._set_hover_obj(picked, self._splice_highlight)

        elif isinstance(picked, _wire_layout.WireLayout):
            self._overlay.hide_message()
            self._set_hover_obj(picked, self._wire_layout_highlight)

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
            picked = _object_picker.find_object(
                mouse_pos, self.camera.objects_in_view,
                self.camera, self._get_view_object)

            kind, target = _wire_snap.get_snap_info(picked)

            if kind is not None:
                # Purely informational -- never gates the snap/commit, same
                # "always allow, just flag it" philosophy every other snap
                # path in this handler and dragging.WireDragObject already
                # follows.
                if kind == 'terminal':
                    _ok, block_msg, warning_msg = _wire_snap.check_terminal_compat(target, wire_part)
                elif kind == 'splice':
                    _ok, block_msg, warning_msg = _wire_snap.check_splice_compat(target, wire_part)
                else:
                    block_msg, warning_msg = None, None

                if block_msg:
                    self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                elif warning_msg:
                    self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
                else:
                    self._overlay.hide_message()

                target_point = _wire_snap.snap_point(kind, target)
                ep = (self._source_wire.obj3d.stop_position
                      if self._source_endpoint == 'stop'
                      else self._source_wire.obj3d.start_position)
                ep += target_point - ep

                self._extension_snap_kind = kind
                self._extension_snap_target = target

                self.mainframe.editor3d.Refresh(False)
                return

            self._extension_snap_kind = None
            self._extension_snap_target = None
            self._overlay.hide_message()

            self._update_source_endpoint(world_pos_pt.as_numpy)
            return

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view,
            self.camera, self._get_view_object)

        picked = _wire_snap.resolve_picked(picked)

        if picked is self.obj:
            picked = None

        if isinstance(picked, _terminal.Terminal):
            warning_msg = None
            if wire_part is not None:
                ok, block_msg, warning_msg = _wire_snap.check_terminal_compat(picked, wire_part)
                if not ok:
                    self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                    self._clear_hover()
                    self._update_preview_stop(picked.obj3d.position)
                    return

            if warning_msg:
                self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
            else:
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
            warning_msg = None
            if wire_part is not None:
                ok, block_msg, warning_msg = _wire_snap.check_splice_compat(picked, wire_part)
                if not ok:
                    self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                    self._clear_hover()
                    self._update_preview_stop(picked.obj3d.wire_position)
                    return

            if warning_msg:
                self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
            else:
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
            mouse_pos, self.camera.objects_in_view,
            self.camera, self._get_view_object)

        picked = _wire_snap.resolve_picked(picked)

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

            ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(picked, wire_part)
            if not ok:
                block_msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
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
            # The source wire's endpoint has already been moved by hover();
            # if hover last left it snapped onto something, commit that
            # connection now -- same commit_snap the drag flow uses,
            # generalized here to whichever end this extension is growing
            # (handles terminal/splice/wire-end-merge uniformly). Otherwise
            # the endpoint is already exactly where hover left it -- just
            # commit as-is, same as before extension mode could snap.
            if self._extension_snap_kind is not None:
                _wire_snap.commit_snap(
                    self.mainframe, self._source_wire, self._source_endpoint,
                    self._extension_snap_kind, self._extension_snap_target)

            self._cleanup()
            self._destroy_overlay()
            self._finalized = True
            return

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view,
            self.camera, self._get_view_object)

        picked = _wire_snap.resolve_picked(picked)

        if picked is self.obj:
            picked = None

        circuit_id = self._start_circuit_id

        if isinstance(picked, _terminal.Terminal):
            if wire_part is not None:
                ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(picked, wire_part)
                if not ok:
                    block_msg += '\n\nDo you want to use this wire?'
                    button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                    if button == QMessageBox.StandardButton.No:
                        return

            if circuit_id is None:
                circuit_id = picked.db_obj.circuit_id

            # Discard the temporary preview growing point -- terminal.add_wire
            # overwrites the growing end's own position3d_id with the
            # terminal's own true attach point and extends this same
            # wire's own waypoint list through its back (and, if seated in
            # a cavity, the cavity's own wire-position) point.
            stale_stop_id = self._growing_point.db_id[:-2]
            picked.add_wire(self.obj, self._growing_end)
            self.ptables.pjt_points3d_table[stale_stop_id].delete()

        elif isinstance(picked, _wire_layout.WireLayout):
            # _wire_layout_end_wire only ever matches a WireLayout sitting
            # at exactly ONE wire's own true end (never an interior bend
            # or a genuine multi-wire seam -- see its own docstring), so
            # this is always "join two separately-drawn wires into one
            # continuous physical wire", exactly the isinstance(Wire) case
            # below, just reached via a marker (real or one of
            # handlers.wire_snap's own probes standing in for an
            # otherwise marker-less dangling end) instead of a raw hit on
            # the wire body itself -- merge_wire_into needed here for the
            # same reason, not just a shared Point between two rows that
            # stay separate. Confirmed 2026-08-06: the old share-a-point
            # version left two separate database rows with no seam
            # waypoint/WireLayout, which is wrong for this case.
            end_wire, other_end = _wire_layout_end_wire(picked, project, self.part_id)
            if end_wire is not None:
                merged = merge_wire_into(
                    project, self.obj, end_wire, other_end, own_end=self._growing_end)
                self.obj = merged
                self.obj.identify(None)
                self._cleanup()
                self._destroy_overlay()
                self._finalized = True
                return
            # else: mid-wire or mismatched part — preview stop already at world pos; keep as-is

        elif isinstance(picked, _splice.Splice):
            if wire_part is not None:
                ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(picked, wire_part)
                if not ok:
                    block_msg += '\n\nDo you want to use this wire?'
                    button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                    if button == QMessageBox.StandardButton.No:
                        return

            stale_stop_id = self._growing_point.db_id[:-2]
            self._set_growing_obj3d_position(picked.obj3d.wire_position)
            self._set_growing_position3d_id(picked.db_obj.branch_position3d_id)
            self.ptables.pjt_points3d_table[stale_stop_id].delete()

            self._set_growing_position2d_id(picked.db_obj.position2d_id)
            self._set_growing_objschematic_position(picked.db_obj.position2d)

            picked.add_wire(self.obj)
            self.obj.set_sibling(picked, self._growing_end)

            # A layout at the wire's own true end -- purely a visual cap
            # showing it properly seated into the splice, matching
            # handlers.wire_snap.commit_snap's own splice branch. Every
            # branch wire on this splice shares the exact same
            # branch_position3d_id (never cloned), so a 2nd/3rd wire
            # snapping here must not create a duplicate layout.
            branch_id = picked.db_obj.branch_position3d_id
            existing_layout = self.ptables.pjt_wire_layouts_table.select(
                'id', position3d_id=branch_id)
            if not existing_layout:
                layout_db = self.ptables.pjt_wire_layouts_table.insert(branch_id)
                layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
                project.add_wire_layout(layout_obj)

        elif isinstance(picked, _wire.Wire):
            # Joining this (still-dangling) wire's stop to another,
            # separately-drawn dangling wire's endpoint -- they're the
            # same physical wire once connected, so they merge into one
            # row (with a WireLayout at the seam) rather than staying
            # linked; see merge_wire_into.
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
            merged = merge_wire_into(
                project, self.obj, picked, other_end, own_end=self._growing_end)
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

        # self.obj is already registered when continuing a pre-existing
        # wire (_start_add_to_wire) -- re-adding it would double-count
        # project.obj_count for the same wire.
        if not self._preexisting_wire:
            project.add_wire(self.obj)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    @_check_types.do
    def _commit_growing_point_as_waypoint(self) -> None:
        """
        Tag the current live preview growing point as a permanent interior
        waypoint on this *same* wire (no new ``pjt_wires`` row -- see
        handlers.wire_layout_handler._create_wire_layout_on_wire, the same
        operation performed inline here since the wire is still being
        drawn), drop a :class:`WireLayout` there, and continue the preview
        from a fresh point past it -- same wire object and row throughout.

        Growing from ``'stop'`` (every entry point except
        ``_start_add_to_wire``'s ``'start'`` case) appends at the end of
        the existing waypoint order, matching the original, long-standing
        shape; growing from ``'start'`` inserts at index 0 and shifts every
        existing waypoint's ``idx`` up by one first, mirroring
        ``Terminal.add_wire``'s own symmetric start/stop handling.

        The shared core both ``_commit_waypoint`` (a free-space click
        mid-placement) and ``_start_add_to_wire`` (the initial tag, before
        any further mouse input) use -- see ``_promote_last_committed`` for
        the inverse operation.
        """
        project = self.mainframe.project

        self._has_committed_waypoint = True

        growing_point_id = self._preview_stop_point_id
        growing_pos = self._growing_point

        existing = self.obj.db_obj.waypoints3d

        if self._growing_end == 'stop':
            new_idx = len(existing)
        else:
            for wp in existing:
                wp.idx = wp.idx + 1
            new_idx = 0

        point = self.ptables.pjt_points3d_table[growing_point_id]
        point.wire_id = self.obj.db_obj.db_id
        point.idx = new_idx

        layout_db = self.ptables.pjt_wire_layouts_table.insert(growing_point_id)
        layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
        project.add_wire_layout(layout_obj)
        self._committed_layouts.append(layout_obj)
        self._session_waypoint_count += 1

        new_point_db = self.ptables.pjt_points3d_table.insert(
            float(growing_pos.x), float(growing_pos.y), float(growing_pos.z))
        self._preview_stop_point_id = new_point_db.db_id

        # The just-committed point becomes a permanent interior waypoint;
        # the wire's own growing end moves on to the fresh point,
        # continuing the live preview.
        self._set_growing_position3d_id(new_point_db.db_id)
        self._set_growing_obj3d_position(new_point_db.point)
        self.obj.obj3d.refresh_waypoints()

    @_check_types.do
    def _commit_waypoint(self) -> None:
        """
        Commit the current live preview growing point as a permanent
        interior waypoint on this *same* wire and continue the preview
        from a fresh point past it. Called when a mid-placement click
        lands in free space instead of on an attachable target; stays in
        phase 1 (loops back for the next click) rather than finalizing.
        """
        self._commit_growing_point_as_waypoint()

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

        self._promote_last_committed()

        if not self._preexisting_wire:
            self.mainframe.project.add_wire(self.obj)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    @_check_types.do
    def _promote_last_committed(self) -> None:
        """
        Discard the current in-progress (never-confirmed) growing point
        and promote the last waypoint committed this session back to
        being this wire's own true growing end -- see
        WireTypeMixin._segments()/waypoints3d: ordered by idx, so
        ``[-1]``/``[0]`` is the most recently committed one when growing
        from ``'stop'``/``'start'`` respectively.

        The shared undo-one-step both ``finalize_at_last_point`` (once,
        right-click) and ``cancel()``'s ``_preexisting_wire`` rollback
        (repeatedly, undoing the whole "Add to Wire" session) use.
        """
        stale_id = self._growing_point.db_id[:-2]

        if self._growing_end == 'stop':
            last_waypoint = self.obj.db_obj.waypoints3d[-1]
        else:
            last_waypoint = self.obj.db_obj.waypoints3d[0]

        last_point = last_waypoint.point

        last_waypoint.wire_id = None
        last_waypoint.idx = None

        if self._growing_end == 'start':
            for wp in self.obj.db_obj.waypoints3d:
                wp.idx = wp.idx - 1

        self._set_growing_position3d_id(last_waypoint.db_id)
        self._set_growing_obj3d_position(last_point)

        self.ptables.pjt_points3d_table[stale_id].delete()

        self._session_waypoint_count -= 1

        # _commit_growing_point_as_waypoint() eagerly drops a WireLayout at
        # every free-space click, on the assumption the run continues past
        # it. Discarding the in-progress segment above can leave the very
        # last one of those marking what's now this wire's own terminus
        # instead of a joint between two sections -- remove it in that
        # case; the wire still ends at the exact same point, just without
        # a layout marker rendered there.
        if self._committed_layouts:
            last_layout = self._committed_layouts[-1]
            if len(last_layout.db_obj.attached_wires) < 2:
                last_layout.delete()
                self._committed_layouts.pop()

        self.obj.obj3d.refresh_waypoints()

    @_check_types.do
    def cancel(self):
        if self._extension_mode and self._extension_original_pos is not None:
            # Roll back the source wire's endpoint to where it was before phase 1
            orig_pt = _point.Point(*self._extension_original_pos)

            ep = (self._source_wire.obj3d.stop_position
                  if self._source_endpoint == 'stop'
                  else self._source_wire.obj3d.start_position)

            ep += orig_pt - ep

        if self._preexisting_wire:
            # self.obj is a real, already-placed wire being continued
            # (_start_add_to_wire), not a throwaway preview -- deleting it
            # below would destroy the user's actual wire. Undo everything
            # committed this session instead (repeat the same undo-one-step
            # finalize_at_last_point uses, once per waypoint this session
            # added), restoring it to exactly its pre-session shape.
            while self._session_waypoint_count > 0:
                self._promote_last_committed()

            self._cleanup()
            self._destroy_overlay()
            return

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
