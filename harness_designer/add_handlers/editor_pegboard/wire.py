# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Two-click interactive wire placement for the peg board editor.

Deliberately much simpler than ``add_handlers.editor_3d.wire``: no
waypoints, no extension mode, no merging onto an existing wire's own
open end or mid-span -- the user can only ever click on a terminal, a
splice, or empty board space (which just leaves that end unconnected).
Splices are real, clickable peg-board objects now (see
``objects_pegboard.splice.Splice`` -- start/stop/branch all wired up to
mirror the 3D view), so a splice click resolves the exact same way a
terminal click does, just against ``branch_position_pegboard`` instead
of a terminal's ``attach_position_pegboard``.

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

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from ...objects import terminal as _terminal
from ...objects import splice as _splice
from ...handlers import wire_snap as _wire_snap
from ...handlers import wire_slack as _wire_slack
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects
    from ... import ui as _ui


Config = _config.Config.colors


class Wire(_base.AddHandlerBase):
    """Two-click wire placement session -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part_id: bytes,
        phase: int = 0, growing_end: str = 'stop', preexisting_wire: bool = False,
    ):
        super().__init__(canvas, target)

        self.mainframe: "_ui.MainFrame" = canvas.mainframe
        self.camera = canvas.camera
        self.ptables = canvas.mainframe.project.ptables

        self.part_id = part_id
        self._phase = phase
        self._growing_end = growing_end
        self._preexisting_wire = preexisting_wire
        self._finalized = False

        self._hover_obj = None
        self._hover_kind = None

        self._start_kind = None
        self._start_target = None

        self._terminal_highlight = _materials.Plastic(_color.Color(*Config.add_object.terminal_highlight))
        self._splice_highlight = _materials.Plastic(_color.Color(*Config.add_object.splice_highlight))

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.objpegboard

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

        return False

    # ------------------------------------------------------------------
    # Picking
    # ------------------------------------------------------------------

    @_check_types.do
    def _pick(self, mouse_pos: _point.Point):
        """Return ``(kind, target, world_pos)`` for whatever's under the
        cursor -- ``kind`` is ``'terminal'``/``'splice'``/``None`` (free
        space), ``target`` the resolved ``Terminal``/``Splice`` facade or
        ``None``, ``world_pos`` always the raw board-plane point (used
        for the free-space case, and to drive the live preview
        regardless of what's under the cursor).
        """
        world_pos = self.camera.screen_to_world(mouse_pos)

        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)
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

        self._hover_kind = None

    @_check_types.do
    def _growing_point(self) -> _point.Point:
        if self._growing_end == 'stop':
            return self.target.objpegboard.stop_position
        return self.target.objpegboard.start_position

    @_check_types.do
    def _set_growing_position(self, point: _point.Point) -> None:
        growing = self._growing_point()
        growing += point - growing

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
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

        self._growing_end = 'stop'
        self._phase = 1

    @_check_types.do
    def _handle_second_click(self, mouse_pos: _point.Point) -> None:
        stop_kind = self._hover_kind
        stop_target = self._hover_obj

        self._clear_hover()

        self._attach_end('start', self._start_kind, self._start_target)
        self._attach_end('stop', stop_kind, stop_target)

        _wire_slack.reconcile(self.mainframe, self.target)

        self.target.identify(None)

        if not self._preexisting_wire:
            self.mainframe.project.add_wire(self.target)

        self._finalized = True

    @_check_types.do
    def _attach_end(self, end: str, kind: str | None, obj) -> None:
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
                ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(obj, wire_part)
                if not ok:
                    block_msg += '\n\nDo you want to use this wire?'
                    button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                    if button == QMessageBox.StandardButton.No:
                        return

            obj.add_wire(self.target, end)

        elif kind == 'splice':
            wire_part = self._get_wire_part()
            if wire_part is not None:
                ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(obj, wire_part)
                if not ok:
                    block_msg += '\n\nDo you want to use this wire?'
                    button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                    if button == QMessageBox.StandardButton.No:
                        return

            branch_pegboard = obj.db_obj.branch_position_pegboard
            branch3d = obj.db_obj.branch_position3d

            if end == 'start':
                self.target.db_obj.start_position_pegboard_id = obj.db_obj.branch_position_pegboard_id
                self.target.objpegboard.set_start_position(branch_pegboard)
                self.target.db_obj.start_position3d_id = obj.db_obj.branch_position3d_id
                self.target.obj3d.set_start_position(branch3d)
            else:
                self.target.db_obj.stop_position_pegboard_id = obj.db_obj.branch_position_pegboard_id
                self.target.objpegboard.set_stop_position(branch_pegboard)
                self.target.db_obj.stop_position3d_id = obj.db_obj.branch_position3d_id
                self.target.obj3d.set_stop_position(branch3d)

            obj.add_wire(self.target)
            self.target.set_sibling(obj, end)

        # free space: the preview already left this end's peg-board
        # point wherever the user clicked (see hover/_set_growing_
        # position) and its 3D point wherever start_add seeded it --
        # nothing further to attach.

    @_check_types.do
    def _get_wire_part(self):
        if self.part_id is None:
            return None

        try:
            return self.mainframe.global_db.wires_table[self.part_id]
        except (IndexError, KeyError):
            return None

    # ------------------------------------------------------------------
    # Finishing early / cancellation
    # ------------------------------------------------------------------

    @_check_types.do
    def finalize_at_last_point(self) -> None:
        """Right-click: no mid-route waypoints exist to fall back to
        here (see the module docstring) -- same as an outright cancel.
        """
        self.cancel()
        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        self._clear_hover()

        if not self._preexisting_wire and self.target is not None:
            self.target.delete()

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
