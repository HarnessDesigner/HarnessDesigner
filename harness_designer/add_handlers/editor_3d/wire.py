# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Two-click interactive wire placement for the 3D editor.

Ported from ``handlers.wire_handler.AddWireHandler`` -- the underlying
mechanics (phase 0/1 hover-preview + click-to-commit state machine, snap
probes, waypoint commit/cancel/finalize, extension mode) are unchanged;
what's different is only *how* a session gets constructed and driven:

- Setup -- resolving the part, and for a terminal/splice/extend/add-to-
  wire start, building the real attachment -- is
  ``objects.objects_3d.wire.Wire.start_add``'s job now, not this
  class's own ``__init__``. By the time this handler exists there is
  always a real target view object to attach to: the new preview wire
  itself (terminal/splice/free-space starts), or the existing wire
  being extended/continued (extension mode / add-to-wire, which never
  created a preview in the old code either -- see ``self.target``'s
  own per-mode meaning below).
- One genuine behavior change, forced by the above: a free-space start
  used to create nothing until the first click (phase 0 was pure hover
  highlighting, no visible preview). Now the preview wire exists from
  the moment placement begins, at a placeholder point, so phase 0 also
  live-previews the start point following the cursor (``_growing_end``
  is ``'start'`` during phase 0 instead of only ever being read as
  ``'stop'``) -- ``_hover_phase0``/``_handle_first_click`` are
  restructured to mirror ``_hover_phase1``/``_handle_second_click``'s
  own shape for this reason, not because the underlying attach rules
  changed.
- Driving -- what used to be separate ``hover()``/``release_capture()``/
  ``finalize_at_last_point()``/``cancel()`` entry points called by
  ``mainframe``'s own ``_obj_handler`` plumbing -- is now the single
  ``__call__`` every add/drag/rotation handler shares (see
  ``add_handlers.base.AddHandlerBase``).
"""

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtWidgets import QMessageBox

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from ...objects import wire_layout as _wire_layout
from ...objects import terminal as _terminal
from ...objects import splice as _splice
from ...objects import wire as _wire
from ...handlers import wire_snap as _wire_snap
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ... import ui as _ui


Config = _config.Config.colors
_SNAP_THRESHOLD = 5.0


class Wire(_base.AddHandlerBase):
    """Two-click wire placement session -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part_id: bytes,
        phase: int, growing_end: str = 'stop', preexisting_wire: bool = False,
        start_circuit_id=None, extension_mode: bool = False, source_wire=None,
        source_endpoint: str | None = None,
    ):
        super().__init__(canvas, target)

        self.mainframe: "_ui.MainFrame" = canvas.mainframe
        self.camera = canvas.camera
        self.ptables = canvas.mainframe.project.ptables

        self.part_id = part_id
        self._phase = phase
        self._growing_end = growing_end
        self._preexisting_wire = preexisting_wire
        self._start_circuit_id = start_circuit_id
        self._finalized = False

        self._hover_obj = None

        # Extension mode: live-move an existing wire's own dangling end
        # rather than growing a fresh preview -- self.target IS
        # self._source_wire in this mode (see start_add), never a
        # freshly-created preview.
        self._extension_mode = extension_mode
        self._source_wire = source_wire
        self._source_endpoint = source_endpoint
        self._extension_dir: "np.ndarray | None" = None
        self._extension_origin: "np.ndarray | None" = None
        self._extension_original_pos: "np.ndarray | None" = None

        self._committed_layouts: list = []
        self._has_committed_waypoint = False
        self._session_waypoint_count = 0

        self._snap_probes: "_wire_snap.SnapProbeSet | None" = None
        self._snap_probes_part_id: bytes | None = None

        self._extension_snap_kind: str | None = None
        self._extension_snap_target = None

        self._overlay = _wire_snap.SnapOverlay(canvas)

        self._terminal_highlight = _materials.Plastic(_color.Color(*Config.add_object.terminal_highlight))
        self._wire_layout_highlight = _materials.Plastic(_color.Color(*Config.add_object.wire_highlight))
        self._splice_highlight = _materials.Plastic(_color.Color(*Config.add_object.splice_highlight))

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

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
            if self._phase == 0:
                self._handle_first_click(current_pos)
            else:
                self._handle_second_click(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.RIGHT_UP and not had_motion:
            self.finalize_at_last_point()
            return True

        return False

    @staticmethod
    def _get_view_object(obj):
        return obj.obj3d

    @_check_types.do
    def _get_wire_part(self):
        if self.part_id is None:
            return None

        try:
            return self.mainframe.global_db.wires_table[self.part_id]
        except (IndexError, KeyError):
            return None

    @_check_types.do
    def _ensure_snap_probes(self) -> None:
        wire_part = self._get_wire_part()
        if wire_part is None:
            return

        if self._snap_probes is not None and self._snap_probes_part_id == wire_part.db_id:
            return

        if self._snap_probes is not None:
            self._snap_probes.close()

        exclude_wire = self._source_wire if self._extension_mode else self.target

        self._snap_probes = _wire_snap.SnapProbeSet(
            self.mainframe, wire_part, exclude_wire=exclude_wire)
        self._snap_probes_part_id = wire_part.db_id

    @_check_types.do
    def _set_hover_obj(self, obj, material) -> None:
        if obj is not self._hover_obj:
            if self._hover_obj is not None:
                self._hover_obj.identify(None)

            if obj is not None:
                obj.identify(material)

            self._hover_obj = obj

    @_check_types.do
    def _clear_hover(self) -> None:
        if self._hover_obj is not None:
            self._hover_obj.identify(None)
            self._hover_obj = None

    # ------------------------------------------------------------------
    # Growing-end plumbing -- 'start' during phase 0 (free-space start
    # only) or _start_add_to_wire's own continue-from-start case;
    # 'stop' everywhere else, including all of phase 1.
    # ------------------------------------------------------------------

    @property
    @_check_types.do
    def _growing_point(self) -> _point.Point:
        if self._growing_end == 'stop':
            return self.target.obj3d.stop_position
        return self.target.obj3d.start_position

    @_check_types.do
    def _set_growing_position3d_id(self, point_id: bytes) -> None:
        if self._growing_end == 'stop':
            self.target.db_obj.stop_position3d_id = point_id
        else:
            self.target.db_obj.start_position3d_id = point_id

    @_check_types.do
    def _set_growing_position2d_id(self, point_id) -> None:
        if self._growing_end == 'stop':
            self.target.db_obj.stop_position2d_id = point_id
        else:
            self.target.db_obj.start_position2d_id = point_id

    @_check_types.do
    def _set_growing_obj3d_position(self, point: _point.Point) -> None:
        if self._growing_end == 'stop':
            self.target.obj3d.set_stop_position(point)
        else:
            self.target.obj3d.set_start_position(point)

    @_check_types.do
    def _set_growing_objschematic_position(self, point: _point.Point) -> None:
        if self._growing_end == 'stop':
            self.target.objschematic.set_stop_position(point)
        else:
            self.target.objschematic.set_start_position(point)

    @_check_types.do
    def _update_preview_stop(self, world_pos) -> None:
        if not isinstance(world_pos, _point.Point):
            world_pos = _point.Point(*world_pos)

        growing = self._growing_point
        growing += world_pos - growing

        self.mainframe.editor3d.Refresh(False)

    @_check_types.do
    def _project_extension(self, world_np):
        t = float(np.dot(world_np - self._extension_origin, self._extension_dir))
        return self._extension_origin + max(0.0, t) * self._extension_dir

    @_check_types.do
    def _update_source_endpoint(self, world_np) -> None:
        proj = self._project_extension(world_np)
        proj_pt = _point.Point(*proj)

        ep = (self._source_wire.obj3d.stop_position
              if self._source_endpoint == 'stop'
              else self._source_wire.obj3d.start_position)

        ep += proj_pt - ep

        self.mainframe.editor3d.Refresh(False)

    # ------------------------------------------------------------------
    # Hover
    # ------------------------------------------------------------------

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        self._ensure_snap_probes()

        with self.mainframe.editor3d.context:
            if self._extension_mode:
                self._hover_extension(mouse_pos)
            elif self._phase == 0:
                self._hover_phase0(mouse_pos)
            else:
                self._hover_phase1(mouse_pos)

    @_check_types.do
    def _hover_extension(self, mouse_pos: _point.Point) -> None:
        world_pos_pt = self.camera.get_position_on_focal_plane(mouse_pos)

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)
        kind, target = _wire_snap.get_snap_info(picked)

        wire_part = self._get_wire_part()

        if kind is not None:
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

    @_check_types.do
    def _hover_phase0(self, mouse_pos: _point.Point) -> None:
        """Free-space start only (every other entry point skips phase 0
        entirely) -- mirrors _hover_phase1's own shape (highlight a
        valid attach target with a compat warning, else live-preview the
        growing point at the cursor), growing 'start' instead of 'stop'.
        """
        wire_part = self._get_wire_part()
        world_pos_pt = self.camera.get_position_on_focal_plane(mouse_pos)

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)
        picked = _wire_snap.resolve_picked(picked)

        if picked is self.target:
            picked = None

        if isinstance(picked, _terminal.Terminal):
            warning_msg = None
            if wire_part is not None:
                ok, block_msg, warning_msg = _wire_snap.check_terminal_compat(picked, wire_part)
                if not ok:
                    self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                    self._clear_hover()
                    self._update_preview_stop(picked.db_obj.attach_position3d)
                    return

            if warning_msg:
                self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
            else:
                self._overlay.hide_message()

            self._set_hover_obj(picked, self._terminal_highlight)
            self._update_preview_stop(picked.db_obj.attach_position3d)

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

        elif isinstance(picked, _wire_layout.WireLayout):
            self._overlay.hide_message()
            self._set_hover_obj(picked, self._wire_layout_highlight)
            self._update_preview_stop(picked.obj3d.position)

        else:
            self._overlay.hide_message()
            self._clear_hover()
            self._update_preview_stop(world_pos_pt)

    @_check_types.do
    def _hover_phase1(self, mouse_pos: _point.Point) -> None:
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        world_pos_pt = self.camera.get_position_on_focal_plane(mouse_pos)

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)
        picked = _wire_snap.resolve_picked(picked)

        if picked is self.target:
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

            from ...handlers.wire_handler import _wire_layout_end_wire
            end_wire, _end = _wire_layout_end_wire(picked, project, self.part_id)
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
    # Clicks
    # ------------------------------------------------------------------

    @_check_types.do
    def _handle_first_click(self, mouse_pos: _point.Point) -> None:
        """Lock the start point at wherever hover last left it (or
        whatever it's attached to) and move on to phase 1 -- free-space
        start only, see the module docstring.
        """
        wire_part = self._get_wire_part()

        if isinstance(self._hover_obj, _terminal.Terminal):
            terminal = self._hover_obj

            ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(terminal, wire_part) \
                if wire_part is not None else (True, None, None)
            if not ok:
                block_msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                if button == QMessageBox.StandardButton.No:
                    return

            self._start_circuit_id = terminal.db_obj.circuit_id

            stale_start_id = self.target.obj3d.start_position.db_id[:-2]
            terminal.add_wire(self.target, 'start')
            self.ptables.pjt_points3d_table[stale_start_id].delete()

        elif isinstance(self._hover_obj, _splice.Splice):
            splice = self._hover_obj

            ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(splice, wire_part) \
                if wire_part is not None else (True, None, None)
            if not ok:
                block_msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                if button == QMessageBox.StandardButton.No:
                    return

            self._start_circuit_id = None

            stale_start_id = self.target.obj3d.start_position.db_id[:-2]
            self.target.obj3d.start_position.attach(splice.obj3d.wire_position)
            self.target.db_obj.start_position3d_id = splice.db_obj.branch_position3d_id
            self.ptables.pjt_points3d_table[stale_start_id].delete()

            splice.add_wire(self.target)
            self.target.set_sibling(splice, 'start')

        elif isinstance(self._hover_obj, _wire_layout.WireLayout):
            layout = self._hover_obj
            attached = layout.db_obj.attached_wires
            if attached:
                self.part_id = attached[0].part_id

            self.target.obj3d.start_position.attach(layout.obj3d.position)
            self.target.db_obj.start_position3d_id = layout.db_obj.position3d_id
            self._start_circuit_id = None

        else:
            # Free space -- the start point already sits wherever hover
            # left it.
            self._start_circuit_id = None

        self._clear_hover()
        self._overlay.hide_message()

        self._growing_end = 'stop'
        self._phase = 1

    @_check_types.do
    def _handle_second_click(self, mouse_pos: _point.Point) -> None:
        project = self.mainframe.project
        wire_part = self._get_wire_part()

        if self._extension_mode:
            if self._extension_snap_kind is not None:
                _wire_snap.commit_snap(
                    self.mainframe, self._source_wire, self._source_endpoint,
                    self._extension_snap_kind, self._extension_snap_target)

            self._cleanup()
            self._destroy_overlay()
            self._finalized = True
            return

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)
        picked = _wire_snap.resolve_picked(picked)

        if picked is self.target:
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

            stale_stop_id = self._growing_point.db_id[:-2]
            picked.add_wire(self.target, self._growing_end)
            self.ptables.pjt_points3d_table[stale_stop_id].delete()

        elif isinstance(picked, _wire_layout.WireLayout):
            from ...handlers.wire_handler import _wire_layout_end_wire, merge_wire_into

            end_wire, other_end = _wire_layout_end_wire(picked, project, self.part_id)
            if end_wire is not None:
                merged = merge_wire_into(
                    project, self.target, end_wire, other_end, own_end=self._growing_end)
                self.target = merged
                self.target.identify(None)
                self._cleanup()
                self._destroy_overlay()
                self._finalized = True
                return
            # else: mid-wire or mismatched part -- preview stop already at world pos; keep as-is

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

            picked.add_wire(self.target)
            self.target.set_sibling(picked, self._growing_end)

            branch_id = picked.db_obj.branch_position3d_id
            existing_layout = self.ptables.pjt_wire_layouts_table.select(
                'id', position3d_id=branch_id)
            if not existing_layout:
                layout_db = self.ptables.pjt_wire_layouts_table.insert(branch_id)
                layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
                project.add_wire_layout(layout_obj)

        elif isinstance(picked, _wire.Wire):
            from ...handlers.wire_handler import merge_wire_into

            world_np = self.camera.get_position_on_focal_plane(mouse_pos).as_numpy
            start_np = picked.obj3d.start_position.as_numpy
            stop_np = picked.obj3d.stop_position.as_numpy
            near_start = float(np.linalg.norm(world_np - start_np)) < _SNAP_THRESHOLD
            near_stop = float(np.linalg.norm(world_np - stop_np)) < _SNAP_THRESHOLD

            if not near_start and not near_stop:
                self._commit_waypoint()
                return

            if picked.db_obj.part_id != self.target.db_obj.part_id:
                self._overlay.show_message(mouse_pos, 'Different wire part — cannot join')
                return

            other_end = 'start' if near_start else 'stop'
            merged = merge_wire_into(
                project, self.target, picked, other_end, own_end=self._growing_end)
            self.target = merged

            self.target.identify(None)
            self._cleanup()
            self._destroy_overlay()
            self._finalized = True
            return

        else:
            self._commit_waypoint()
            return

        if circuit_id != self._start_circuit_id:
            self.target.db_obj.circuit_id = circuit_id

        self.target.identify(None)

        if not self._preexisting_wire:
            project.add_wire(self.target)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    # ------------------------------------------------------------------
    # Waypoint commit
    # ------------------------------------------------------------------

    @_check_types.do
    def _commit_growing_point_as_waypoint(self) -> None:
        project = self.mainframe.project

        self._has_committed_waypoint = True

        growing_point_id = self._growing_point.db_id[:-2]
        growing_pos = self._growing_point

        existing = self.target.db_obj.waypoints3d

        if self._growing_end == 'stop':
            new_idx = len(existing)
        else:
            for wp in existing:
                wp.idx = wp.idx + 1
            new_idx = 0

        point = self.ptables.pjt_points3d_table[growing_point_id]
        point.wire_id = self.target.db_obj.db_id
        point.idx = new_idx

        layout_db = self.ptables.pjt_wire_layouts_table.insert(growing_point_id)
        layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
        project.add_wire_layout(layout_obj)
        self._committed_layouts.append(layout_obj)
        self._session_waypoint_count += 1

        new_point_db = self.ptables.pjt_points3d_table.insert(
            float(growing_pos.x), float(growing_pos.y), float(growing_pos.z))

        self._set_growing_position3d_id(new_point_db.db_id)
        self._set_growing_obj3d_position(new_point_db.point)
        self.target.obj3d.refresh_waypoints()

    @_check_types.do
    def _commit_waypoint(self) -> None:
        self._commit_growing_point_as_waypoint()

    # ------------------------------------------------------------------
    # Finishing early / cancellation
    # ------------------------------------------------------------------

    @_check_types.do
    def finalize_at_last_point(self) -> None:
        if self._finalized or self._phase == 0:
            return

        if self._extension_mode:
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
            self.mainframe.project.add_wire(self.target)

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True

    @_check_types.do
    def _promote_last_committed(self) -> None:
        stale_id = self._growing_point.db_id[:-2]

        if self._growing_end == 'stop':
            last_waypoint = self.target.db_obj.waypoints3d[-1]
        else:
            last_waypoint = self.target.db_obj.waypoints3d[0]

        last_point = last_waypoint.point

        last_waypoint.wire_id = None
        last_waypoint.idx = None

        if self._growing_end == 'start':
            for wp in self.target.db_obj.waypoints3d:
                wp.idx = wp.idx - 1

        self._set_growing_position3d_id(last_waypoint.db_id)
        self._set_growing_obj3d_position(last_point)

        self.ptables.pjt_points3d_table[stale_id].delete()

        self._session_waypoint_count -= 1

        if self._committed_layouts:
            last_layout = self._committed_layouts[-1]
            if len(last_layout.db_obj.attached_wires) < 2:
                last_layout.delete()
                self._committed_layouts.pop()

        self.target.obj3d.refresh_waypoints()

    @_check_types.do
    def cancel(self) -> None:
        if self._extension_mode and self._extension_original_pos is not None:
            orig_pt = _point.Point(*self._extension_original_pos)

            ep = (self._source_wire.obj3d.stop_position
                  if self._source_endpoint == 'stop'
                  else self._source_wire.obj3d.start_position)

            ep += orig_pt - ep

            self._cleanup()
            self._destroy_overlay()
            return

        if self._preexisting_wire:
            while self._session_waypoint_count > 0:
                self._promote_last_committed()

            self._cleanup()
            self._destroy_overlay()
            return

        for layout_obj in reversed(self._committed_layouts):
            layout_obj.delete()
        self._committed_layouts = []

        if self.target is not None:
            self.target.delete()

        self._cleanup()
        self._destroy_overlay()

    @_check_types.do
    def _cleanup(self) -> None:
        self._clear_hover()
        if self._overlay is not None:
            self._overlay.hide_message()

        if self._snap_probes is not None:
            self._snap_probes.close()
            self._snap_probes = None
            self._snap_probes_part_id = None

    @_check_types.do
    def _destroy_overlay(self) -> None:
        if self._overlay is not None:
            self._overlay.deleteLater()
            self._overlay = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
