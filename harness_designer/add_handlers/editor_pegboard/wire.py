# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Two-click interactive wire placement for the peg board editor.

Deliberately simpler than ``add_handlers.editor_3d.wire`` in how a hit
is resolved: no snap-probe spheres or ambient highlighting, no merging
onto an existing wire's own open end or mid-span -- the user can only
ever click on a terminal, a splice, or empty board space (which just
leaves that end unconnected). Splices are real, clickable peg-board
objects now (see ``objects_pegboard.splice.Splice`` -- start/stop/branch
all wired up to mirror the 3D view), so a splice click resolves the
exact same way a terminal click does, just against
``branch_position_pegboard`` instead of a terminal's
``attach_position_pegboard``.

Extension mode (live-move an existing wire's own free end,
``objects_pegboard.wire.Wire._start_extend_from_wire``) and waypoint
continuation ("Add to Wire",
``objects_pegboard.wire.Wire._start_add_to_wire``) ARE supported
(2026-10-12) -- both only ever operate on a genuinely FREE end
(unattached in every view, not just this one, per
``WireDragMixin.is_anchor_point``/``pick_free_end``), so resolving a hit
onto a terminal/splice via :meth:`Wire._attach_end` and writing both
views' columns together is exactly as correct here as it is for a brand
new wire's own first/second click -- there is no existing real
attachment on either side to clobber.

The real 3D connection is made the moment each end resolves to a
terminal/splice (mirrors ``Terminal.add_wire``'s own now-peg-board-aware
attachment, and ``Splice.add_wire``'s branch-registration) -- not
deferred to some later sync step -- because the 3D view is this wire's
one source of truth for real length (``PJTWire.length_mm``), and nothing
downstream can reconcile the two views' lengths correctly until both
real endpoints actually exist. Once both ends are resolved (click two),
:func:`handlers.wire_slack.reconcile` bows whichever view's straight-line
path came up short so its length matches the other -- see that module's
own docstring for the full reasoning.

A free/unconnected end never needs special-case Y handling to stay flat
-- ``Camera.screen_to_world`` (this locked top-down camera's own mouse
-> world conversion) already always returns ``y=0.0``, and a terminal's/
splice's own peg-board attach point is whatever it really is (currently
always 0.0 too, since nothing else in the peg-board view sets Y to
anything else -- see MEMORY.md) -- so nothing here ever has to touch Y
at all, on either kind of endpoint.
"""

from typing import TYPE_CHECKING, Union as _Union

import numpy as np
from PySide6 import QtWidgets

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from ...objects import terminal as _terminal
from ...objects import splice as _splice
from ...objects import wire_layout as _wire_layout
from ...handlers import wire_snap as _wire_snap
from ...handlers import wire_circuit as _wire_circuit
from ...handlers import wire_slack as _wire_slack
from ...wire_routing import reroute as _wire_reroute
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects
    from ... import ui as _ui
    from ...objects.objects_pegboard import base_pegboard as _base_pegboard
    from ...database.global_db import wire as _glb_wire
    from ...objects import wire as _wire


Config = _config.Config.colors


class Wire(_base.AddHandlerBase):
    """Two-click wire placement session -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase",
                 part_id: bytes, phase: int = 0, growing_point: _point.Point | None = None,
                 preexisting_wire: bool = False, start_circuit_id: bytes | None = None,
                 extension_mode: bool = False, source_wire: _Union["_wire.Wire", None] = None,
                 source_point: _point.Point | None = None):

        super().__init__(canvas, target)

        self.mainframe: "_ui.MainFrame" = canvas.mainframe
        self.camera = canvas.camera
        self.ptables = canvas.mainframe.project.ptables

        self.part_id = part_id
        self._phase = phase
        if growing_point is not None:
            self._growing_point = growing_point
        else:
            self._growing_point = target.objpegboard.stop_position  # NOQA

        self._preexisting_wire = preexisting_wire
        self._start_circuit_id = start_circuit_id
        self._finalized = False

        self._hover_obj = None
        self._hover_kind = None

        self._start_kind = None
        self._start_target = None

        self._committed_layouts: list = []
        self._has_committed_waypoint = False
        self._session_waypoint_count = 0

        # Extension mode: live-move an existing wire's own dangling end
        # rather than growing a fresh preview -- self.target IS
        # self._source_wire in this mode (see objects_pegboard.wire.
        # Wire.start_add), never a freshly-created preview. Mirrors
        # add_handlers.editor_3d.wire.Wire's own extension-mode state,
        # minus its snap-probe/ambient-highlight machinery -- hover here
        # resolves a snap target via the same plain self._pick() every
        # other hover in this class already uses (see the module
        # docstring).
        self._extension_mode = extension_mode
        self._source_wire = source_wire
        self._source_point = source_point
        self._extension_dir: np.ndarray | None = None
        self._extension_origin: np.ndarray | None = None
        self._extension_original_pos: np.ndarray | None = None

        self._terminal_highlight = _materials.Plastic(
            _color.Color(*Config.add_object.terminal_highlight))

        self._splice_highlight = _materials.Plastic(
            _color.Color(*Config.add_object.splice_highlight))

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    @_check_types.do
    def _get_view_object(
        obj: "_objects.ObjectBase"
    ) -> "_base_pegboard.BasePegboard":

        return obj.objpegboard

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @_check_types.do
    def __call__(self, last_pos: _point.Point, current_pos: _point.Point,
                 had_motion: bool, interaction_type: _interaction.MouseInteraction,
                 clicked_object: _Union["_objects.ObjectBase", None]) -> bool:

        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self._finalized = True
            self.cancel()

            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)

            return True

        if (
            interaction_type is _interaction.MouseInteraction.LEFT_UP and
            not had_motion
        ):
            if self._phase == 0:
                self._handle_first_click(current_pos)
            else:
                self._handle_second_click(current_pos)

            return True

        return False

    # ------------------------------------------------------------------
    # Picking
    # ------------------------------------------------------------------

    @_check_types.do
    def _pick(
        self, mouse_pos: _point.Point
    ) -> tuple[str | None, _terminal.Terminal | _splice.Splice | None, _point.Point]:

        """Return ``(kind, target, world_pos)`` for whatever's under the
        cursor -- ``kind`` is ``'terminal'``/``'splice'``/``None`` (free
        space), ``target`` the resolved ``Terminal``/``Splice`` facade or
        ``None``, ``world_pos`` always the raw board-plane point (used
        for the free-space case, and to drive the live preview
        regardless of what's under the cursor).
        """

        world_pos = self.camera.screen_to_world(mouse_pos)

        picked = _object_picker.find_object(
            mouse_pos, self.camera, self.camera.canvas)

        picked = _wire_snap.resolve_picked(picked)

        if picked is self.target:
            picked = None

        if isinstance(picked, _terminal.Terminal):
            return 'terminal', picked, world_pos

        if isinstance(picked, _splice.Splice):
            return 'splice', picked, world_pos

        return None, None, world_pos

    # ------------------------------------------------------------------
    # Hover / live preview
    # ------------------------------------------------------------------

    @_check_types.do
    def _set_hover_obj(self,  obj: _terminal.Terminal | _splice.Splice | None,
                       material: _materials.GLMaterial) -> None:

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

        self._hover_kind = None

    @_check_types.do
    def _set_growing_position(self, point: _point.Point) -> None:
        growing = self._growing_point
        growing += point - growing

    @_check_types.do
    def _set_growing_position_pegboard_id(self, is_start: bool,
                                          point_id: bytes) -> None:

        if is_start:
            self.target.db_obj.start_position_pegboard_id = point_id
        else:
            self.target.db_obj.stop_position_pegboard_id = point_id

    @_check_types.do
    def _set_growing_objpegboard_position(self, is_start: bool,
                                          point: _point.Point) -> None:

        if is_start:
            self.target.objpegboard.set_start_position(point)  # NOQA
        else:
            self.target.objpegboard.set_stop_position(point)  # NOQA

        self._growing_point = point

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        if self._extension_mode:
            self._hover_extension(mouse_pos)

            return

        kind, target, world_pos = self._pick(mouse_pos)

        if kind == 'terminal':
            self._hover_kind = 'terminal'
            self._set_hover_obj(target, self._terminal_highlight)
            self._set_growing_position(target.objpegboard.position)

        elif kind == 'splice':
            self._hover_kind = 'splice'
            self._set_hover_obj(target, self._splice_highlight)
            self._set_growing_position(target.objpegboard.wire_position)

        else:
            self._hover_kind = None
            self._clear_hover()
            self._set_growing_position(world_pos)

        self.mainframe.editor_pegboard.editor.update()

    # ------------------------------------------------------------------
    # Extension mode -- live-move an existing free end along its own
    # current direction ("grow this wire's free end in its current
    # direction", per objects_pegboard.wire.WireMenu.on_extend_wire's own
    # docstring), snapping onto a terminal/splice the same way ordinary
    # hover does. _extension_dir/_extension_origin are set by the caller
    # (objects_pegboard.wire.Wire._start_extend_from_wire) right after
    # construction.
    # ------------------------------------------------------------------

    @_check_types.do
    def _project_extension(self, world_np: np.ndarray) -> np.ndarray:
        t = float(np.dot(world_np - self._extension_origin, self._extension_dir))

        return self._extension_origin + max(0.0, t) * self._extension_dir

    @_check_types.do
    def _move_source_point(self, point: _point.Point) -> None:
        ep = self._source_point
        ep += point - ep

    @_check_types.do
    def _hover_extension(self, mouse_pos: _point.Point) -> None:
        kind, target, world_pos = self._pick(mouse_pos)

        if kind == 'terminal':
            self._hover_kind = 'terminal'
            self._set_hover_obj(target, self._terminal_highlight)
            self._move_source_point(target.objpegboard.position)

        elif kind == 'splice':
            self._hover_kind = 'splice'
            self._set_hover_obj(target, self._splice_highlight)
            self._move_source_point(target.objpegboard.wire_position)

        else:
            self._hover_kind = None
            self._clear_hover()
            projected = self._project_extension(world_pos.as_numpy)
            self._move_source_point(_point.Point(*projected))

        self.mainframe.editor_pegboard.editor.update()

    # ------------------------------------------------------------------
    # Clicks
    # ------------------------------------------------------------------

    @_check_types.do
    def _handle_first_click(self, mouse_pos: _point.Point) -> None:
        """Lock the start end at whatever hover last resolved to, and
        move on to the second (stop) click.
        """

        self._start_kind = self._hover_kind
        self._start_target = self._hover_obj

        self._clear_hover()

        self._growing_point = self.target.objpegboard.stop_position  # NOQA
        self._phase = 1

    @_check_types.do
    def _handle_second_click(self, mouse_pos: _point.Point) -> None:  # NOQA
        if self._extension_mode:
            self._handle_extension_click()
            return

        stop_kind = self._hover_kind
        stop_target = self._hover_obj

        self._clear_hover()

        if self._preexisting_wire:
            if stop_kind is None:
                # Add-to-Wire continuation, landing on empty board space
                # -- commit a waypoint here and keep going (mirrors
                # add_handlers.editor_3d.wire's own phase-1 free-space
                # click), rather than finishing the wire the way an
                # ordinary fresh two-click placement always does.
                self._commit_growing_point_as_waypoint()
                return

            # Only the end actually growing in this continuation session
            # gets attached -- the other end was already resolved in an
            # earlier session and must be left alone.
            is_start = self._growing_point is self.target.objpegboard.start_position  # NOQA
            self._attach_end(
                'start' if is_start else 'stop', stop_kind, stop_target)

        else:
            self._attach_end('start', self._start_kind, self._start_target)
            self._attach_end('stop', stop_kind, stop_target)

        _wire_slack.reconcile(self.mainframe, self.target)

        self.target.identify(None)

        if not self._preexisting_wire:
            self.mainframe.project.add_wire(self.target)

        _wire_circuit.reconcile_wire_circuit(self.mainframe.project, self.target)

        self._finalized = True

    @_check_types.do
    def _handle_extension_click(self) -> None:
        """Commit an extension-mode drag: landing on a terminal/splice
        makes the real connection (:meth:`_attach_end`, for whichever end
        is actually growing -- never both); landing on empty board space
        leaves the free end wherever the live drag already put it, via
        the same ``+=`` the view's own bound callbacks already wrote
        through -- nothing further to attach.
        """
        if self._hover_kind in ('terminal', 'splice'):
            is_start = self._source_point is self.target.objpegboard.start_position  # NOQA
            self._attach_end(
                'start' if is_start else 'stop', self._hover_kind, self._hover_obj)

        _wire_slack.reconcile(self.mainframe, self.target)

        _wire_circuit.reconcile_wire_circuit(self.mainframe.project, self.target)

        self._clear_hover()
        self.target.identify(None)
        self._finalized = True

    @_check_types.do
    def _attach_end(self, end: str, kind: str | None,
                    obj: _terminal.Terminal | _splice.Splice | None) -> None:

        """Make the real connection for one end of :attr:`target`, once
        both ends are known -- a terminal/splice attachment writes the
        wire's real 3D *and* peg-board points together (see
        ``Terminal.add_wire``/``Splice.add_wire``'s own attach logic);
        free space leaves whatever the live preview already put there
        (both views) untouched.
        """

        if kind == 'terminal':
            wire_part = self._get_wire_part()
            if wire_part is not None:
                ok, block_msg, _warning_msg = (
                    _wire_snap.check_terminal_compat(obj, wire_part))

                if not ok:
                    block_msg += '\n\nDo you want to use this wire?'
                    button = QtWidgets.QMessageBox.question(
                        self.mainframe, 'Incompatible Wire', block_msg)

                    if button == QtWidgets.QMessageBox.StandardButton.No:
                        return

            obj.add_wire(self.target, end)

        elif kind == 'splice':
            wire_part = self._get_wire_part()
            if wire_part is not None:
                ok, block_msg, _warning_msg = (
                    _wire_snap.check_splice_compat(obj, wire_part))

                if not ok:
                    block_msg += '\n\nDo you want to use this wire?'
                    button = QtWidgets.QMessageBox.question(
                        self.mainframe, 'Incompatible Wire', block_msg)

                    if button == QtWidgets.QMessageBox.StandardButton.No:
                        return

            branch_pegboard = obj.db_obj.branch_position_pegboard
            branch3d = obj.db_obj.branch_position3d

            if end == 'start':
                self.target.db_obj.start_position_pegboard_id = (
                    obj.db_obj.branch_position_pegboard_id)

                self.target.objpegboard.set_start_position(branch_pegboard)  # NOQA

                self.target.db_obj.start_position3d_id = (
                    obj.db_obj.branch_position3d_id)

                self.target.obj3d.set_start_position(branch3d)  # NOQA

                self.target.db_obj.start_position2d_id = (
                    obj.db_obj.position2d_id)

                self.target.objschematic.set_start_position(obj.db_obj.position2d)  # NOQA
            else:
                self.target.db_obj.stop_position_pegboard_id = (
                    obj.db_obj.branch_position_pegboard_id)

                self.target.objpegboard.set_stop_position(branch_pegboard)  # NOQA

                self.target.db_obj.stop_position3d_id = (
                    obj.db_obj.branch_position3d_id)

                self.target.obj3d.set_stop_position(branch3d)  # NOQA

                self.target.db_obj.stop_position2d_id = (
                    obj.db_obj.position2d_id)

                self.target.objschematic.set_stop_position(obj.db_obj.position2d)  # NOQA

            obj.add_wire(self.target)
            self.target.set_sibling(  # NOQA
                obj,
                self.target.objpegboard.start_position   # NOQA
                if end == 'start' else self.target.objpegboard.stop_position)  # NOQA

            _wire_reroute.on_wire_attached(self.mainframe.project, self.target)

        # free space: the preview already left this end's peg-board
        # point wherever the user clicked (see hover/_set_growing_
        # position) and its 3D point wherever start_add seeded it --
        # nothing further to attach.

    @_check_types.do
    def _get_wire_part(self) -> _Union["_glb_wire.Wire", None]:
        if self.part_id is None:
            return None

        try:
            return self.mainframe.global_db.wires_table[self.part_id]
        except (IndexError, KeyError):
            return None

    # ------------------------------------------------------------------
    # Waypoint commit -- only ever reached via an Add-to-Wire
    # continuation session (self._preexisting_wire); an ordinary fresh
    # two-click placement never calls either of these (see the module
    # docstring).
    # ------------------------------------------------------------------

    @_check_types.do
    def _commit_growing_point_as_waypoint(self) -> None:
        project = self.mainframe.project

        self._has_committed_waypoint = True

        is_start = self._growing_point is self.target.objpegboard.start_position  # NOQA

        growing_point_id = self._growing_point.db_id[:-2]
        growing_pos = self._growing_point

        wire_id = self.target.db_obj.db_id
        paths_table = self.ptables.pjt_wire_paths_table

        if is_start:
            paths_table.add(wire_id, 'pegboard', 0, growing_point_id)
        else:
            paths_table.append(wire_id, 'pegboard', growing_point_id)

        layout_db = self.ptables.pjt_wire_layouts_table.insert(growing_point_id)
        layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
        project.add_wire_layout(layout_obj)
        self._committed_layouts.append(layout_obj)
        self._session_waypoint_count += 1

        new_point_db = self.ptables.pjt_points_pegboard_table.insert(
            float(growing_pos.x), float(growing_pos.y), float(growing_pos.z))

        self._set_growing_position_pegboard_id(is_start, new_point_db.db_id)
        self._set_growing_objpegboard_position(is_start, new_point_db.point)
        self.target.objpegboard.refresh_waypoints()  # NOQA

    @_check_types.do
    def _promote_last_committed(self) -> None:
        is_start = self._growing_point is self.target.objpegboard.start_position  # NOQA

        stale_id = self._growing_point.db_id[:-2]

        if is_start:
            last_waypoint = self.target.db_obj.waypoints_pegboard[0]  # NOQA
        else:
            last_waypoint = self.target.db_obj.waypoints_pegboard[-1]  # NOQA

        last_point = last_waypoint.point

        self.ptables.pjt_wire_paths_table.remove(
            self.target.db_obj.db_id, 'pegboard', last_waypoint.db_id)

        self._set_growing_position_pegboard_id(is_start, last_waypoint.db_id)
        self._set_growing_objpegboard_position(is_start, last_point)

        self.ptables.pjt_points_pegboard_table[stale_id].delete()

        self._session_waypoint_count -= 1

        if self._committed_layouts:
            last_layout = self._committed_layouts[-1]
            if len(last_layout.db_obj.attached_wires) < 2:
                last_layout.delete()
                self._committed_layouts.pop()

        self.target.objpegboard.refresh_waypoints()  # NOQA

    # ------------------------------------------------------------------
    # Finishing early / cancellation
    # ------------------------------------------------------------------

    @_check_types.do
    def finalize_at_last_point(self) -> None:
        """Right-click: extension mode just stops wherever the live drag
        left the point (no revert -- see :meth:`cancel` for that); an
        Add-to-Wire continuation with at least one committed waypoint
        locks in its current position as the final one; everything else
        (including an ordinary fresh two-click placement, which never
        commits a waypoint at all -- see the module docstring) falls
        back to a full cancel.
        """
        if self._extension_mode:
            self._finalized = True
            self._clear_hover()
            return

        if self._preexisting_wire and self._has_committed_waypoint:
            self._promote_last_committed()
            self._finalized = True
            return

        self._finalized = True
        self.cancel()

    @_check_types.do
    def cancel(self) -> None:
        if self._extension_mode:
            if self._extension_original_pos is not None:
                orig_pt = _point.Point(*self._extension_original_pos)
                ep = self._source_point
                ep += orig_pt - ep

            self._clear_hover()
            return

        self._clear_hover()

        if self._preexisting_wire:
            # Add-to-Wire continuation -- roll back every waypoint this
            # session committed, restoring the real free end it started
            # from (the wire itself is real and pre-existing, so it's
            # never deleted here, same as before this session supported
            # waypoints at all).
            while self._session_waypoint_count > 0:
                self._promote_last_committed()
            return

        if self.target is not None:
            self.target.delete()

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self._finalized = True
            self.cancel()
