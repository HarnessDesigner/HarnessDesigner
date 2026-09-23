# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive wire placement for the schematic editor.

Ported from ``handlers.wire_handler_2d.AddWireHandler2D``. Every session starts
pinned to a Terminal or Splice (the real ``Wire`` facade is built
synchronously in ``objects.objects_schematic.wire.Wire.start_add``), and the
user then draws the wire much as they would in a PCB editor:

- Each **left click** in free space puts a waypoint down and starts the next
  segment, which previews from that waypoint toward the cursor. Segments only
  ever run horizontally or vertically: from the last waypoint the wire runs
  along whichever axis the cursor is furthest along (and never straight back
  over the run it just made), so the waypoint lands on that line under the
  cursor. It must neither cut through a housing, splice or note, nor run
  parallel over another wire -- a segment that would is shown with a message
  at the cursor and the click is ignored.
  A waypoint the wire ends up running straight through (the run before it and
  the run after it go the same way) does nothing, and could not be dragged
  anywhere useful -- moving it would tilt both runs -- so placing the next
  waypoint removes it. A right click brings it back with the point that
  removed it.
- Hovering a **terminal or splice** highlights it and snaps the wire's own
  loose end to its real attach point -- a terminal's own
  ``wire_position2d`` (the far end of its exit-stub cylinder, not its name
  label), a splice's own ``position2d`` -- and previews the FULL route the
  auto-router would lay out from the last placed waypoint to there (see
  ``_preview_route_to``/``objects_schematic.wire.Wire.set_preview``), not
  just a straight line.
- A **left click on a terminal or splice** ends the wire there, at that same
  snap point. Whatever the user has placed stays exactly as placed, and the
  auto-router (``wire_routing``) lays out the rest, from the last waypoint to
  that end -- exactly what was just being previewed. With nothing placed yet
  that is the whole wire, as it always was.
- A **right click** takes back the last waypoint (and cancels the wire once
  there are none left to take back); **Escape** cancels outright.

A terminal's mandatory exit stub is placed automatically as the first
waypoint, so the first run always leaves the terminal the way it faces.

The wire is drawn while it is placed (``Canvas.add_preview_object`` -- the
canvas otherwise never draws a wire with a dangling end), and its waypoints
are real rows (``reroute.add_waypoint``) from the moment they are clicked, so
what is on screen is what will be saved.
"""

import math
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...gl import materials as _materials
from ...handlers import wire_snap as _wire_snap
from ...geometry import point as _point
from ...objects import terminal as _terminal
from ...objects import splice as _splice
from ...wire_routing import reroute as _wire_reroute
from ...wire_routing import routing as _routing
from .. import base as _base
from ... import color as _color
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


Config = _config.Config.colors

_BLOCKED_MESSAGES = {
    'housing': 'A wire cannot pass through a housing',
    'terminal': "A wire cannot cross a terminal's wire stub",
    'wire': 'A wire cannot run parallel over another wire',
}


class Wire(_base.AddHandlerBase):
    """Interactive wire placement session -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part,
        stop_point2d, start_obj
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        # Every position this handler deals with is a 2D schematic point.
        self.camera = canvas.mainframe.editor2d.editor.camera

        self._part = part
        self._stop_point2d = stop_point2d
        self._start_obj = start_obj
        self._finalized = False

        # What the user has placed so far -- the waypoint rows, and their
        # positions, in order from the start end. The first ``_locked`` of
        # them are placed for the user (a terminal's exit stub) and are not
        # taken back by a right click.
        self._placed: list[tuple[float, float]] = []
        self._points: list = []
        self._locked = 0

        # Parallel to ``_placed``: for each waypoint, the earlier one placing it
        # removed as pointless (``(position, was_locked)``), or ``None`` -- so a
        # right click can put that one back.
        self._merged: list[tuple[tuple[float, float], bool] | None] = []

        self._hover_obj = None
        self._last_mouse: _point.Point | None = None

        # canvas is the WRAPPER (mainframe.editorX.editor) -- SnapOverlay has to
        # be parented to its own inner, oversized GL canvas (canvas._canvas)
        # instead, the same widget mouse positions are actually measured
        # against, or show_message's own move() lands off by however far the
        # inner canvas is recentered inside this (usually smaller) wrapper --
        # see CanvasWindowBase.objects_in_window's own docstring.
        self._overlay = _wire_snap.SnapOverlay(canvas._canvas)  # NOQA
        self._terminal_highlight = _materials.Plastic(_color.Color(*Config.add_object.terminal_highlight))
        self._splice_highlight = _materials.Plastic(_color.Color(*Config.add_object.splice_highlight))

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.objschematic

    # ------------------------------------------------------------------
    # Session start
    # ------------------------------------------------------------------

    @_check_types.do
    def begin(self) -> None:
        """Called by ``Wire.start_add`` once the start end is attached: a
        terminal's exit stub becomes the first waypoint, so the first run
        leaves the terminal in the direction it faces and the user's own
        first point is measured from the end of it."""
        stub = _wire_reroute._terminal_exit_stub_point(self.target, 'start')  # NOQA

        if stub is not None:
            self._commit(stub[0], stub[1])
            self._locked = 1

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
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
            self._click(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.RIGHT_UP and not had_motion:
            self._undo()
            return True

        return False

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @property
    def _start_xz(self) -> tuple[float, float]:
        start = self.target.db_obj.start_position2d
        return float(start.x), float(start.z)

    @property
    def _last_xz(self) -> tuple[float, float]:
        if self._placed:
            return self._placed[-1]

        return self._start_xz

    def _own_segments(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        path = [self._start_xz] + self._placed
        return list(zip(path, path[1:]))

    def _cursor_xz(self, mouse_pos: _point.Point) -> tuple[float, float]:
        """Where the next waypoint would go for a cursor at *mouse_pos*: the
        cursor's position squared onto a horizontal or vertical run from the
        last waypoint -- along whichever axis it is furthest along. A run
        that would go straight back over the previous one takes the other axis
        instead."""
        world_pos = self.camera.screen_to_world(mouse_pos)
        cx = float(world_pos.x)
        cz = float(world_pos.z)

        last_x, last_z = self._last_xz
        dx = cx - last_x
        dz = cz - last_z

        along_x = abs(dx) >= abs(dz)

        if self._placed:
            before_x, before_z = self._placed[-2] if len(self._placed) > 1 else self._start_xz
            back_x = last_x - before_x
            back_z = last_z - before_z

            # Reversing the previous run: its own direction, negated.
            if along_x and abs(back_z) < 1e-6 and dx * back_x < 0.0:
                along_x = False
            elif not along_x and abs(back_x) < 1e-6 and dz * back_z < 0.0:
                along_x = True

        if along_x:
            return cx, last_z

        return last_x, cz

    def _blocked(self, xz: tuple[float, float]) -> str | None:
        """Why a segment from the last waypoint to *xz* isn't allowed
        (``'housing'`` / ``'wire'``), or ``None`` if it is."""
        return _routing.free_segment_blocked(
            self.mainframe.project, self._last_xz, xz, ignore_wire=self.target,
            own_segments=self._own_segments())

    def _too_short(self, xz: tuple[float, float]) -> bool:
        last = self._last_xz
        return math.hypot(xz[0] - last[0], xz[1] - last[1]) < _routing._lane_spacing() / 2.0  # NOQA

    @_check_types.do
    def _pick_end(self, mouse_pos: _point.Point):
        """The terminal or splice under the cursor that this wire could end
        on, else ``None`` (its own start end doesn't count)."""
        picked = _object_picker.find_object(mouse_pos, self.camera, self.camera.canvas)
        picked = _wire_snap.resolve_picked(picked)

        if picked is self._start_obj or picked is self.target:
            return None

        if isinstance(picked, (_terminal.Terminal, _splice.Splice)):
            return picked

        return None

    # ------------------------------------------------------------------
    # Hover
    # ------------------------------------------------------------------

    @_check_types.do
    def _set_hover(self, obj) -> None:
        if obj is self._hover_obj:
            return

        if self._hover_obj is not None:
            self._hover_obj.identify(None)

        if obj is not None:
            if isinstance(obj, _terminal.Terminal):
                obj.identify(self._terminal_highlight)
            else:
                obj.identify(self._splice_highlight)

        self._hover_obj = obj

    @_check_types.do
    def _ghost_to(self, xz: tuple[float, float]) -> None:
        """Move the wire's loose end to *xz* -- the live preview of the next
        segment."""
        stop = self._stop_point2d.point

        with stop:
            stop.x = xz[0]
            stop.z = xz[1]

        # Callbacks are suppressed inside the ``with`` (see reroute_wire).
        stop._process_callbacks()  # NOQA

        self.mainframe.editor2d.Refresh(False)

    @staticmethod
    def _snap_point(picked) -> tuple[float, float]:
        """Where a wire actually attaches on *picked* -- a terminal's own
        ``wire_position2d`` (the far end of its exit-stub cylinder; its name
        label, which is all that can be clicked to pick it, is elsewhere),
        a splice's own ``position2d`` (its single attach point)."""
        if isinstance(picked, _terminal.Terminal):
            point = picked.db_obj.wire_position2d
        else:
            point = picked.db_obj.position2d

        return float(point.x), float(point.z)

    @_check_types.do
    def _preview_route_to(self, xz: tuple[float, float]) -> None:
        """Preview the route from the last placed waypoint to *xz* -- a snap
        target's own attach point -- the same one :meth:`_finish` would
        actually lay out if the wire ended there right now. Nothing here
        writes a waypoint row; :meth:`objects_schematic.wire.Wire.set_preview`
        is a display-only overlay on top of the wire's real, already-placed
        path.
        """
        own = self._own_segments()

        start_anchor = None
        if own:
            (ax, az), (bx, bz) = own[-1]
            if _wire_reroute._axis_aligned((ax, az), (bx, bz)):  # NOQA
                start_anchor = (ax, az)

        interior = _routing.route(
            self.mainframe.project, self._last_xz, xz,
            ignore_wire=self.target, start_anchor=start_anchor, extra_segments=own)

        self.target.objschematic.set_preview(interior)
        self._ghost_to(xz)

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        self._last_mouse = mouse_pos

        picked = self._pick_end(mouse_pos)
        self._set_hover(picked)

        if picked is not None:
            if isinstance(picked, _terminal.Terminal):
                _ok, block_msg, warning_msg = _wire_snap.check_terminal_compat(picked, self._part)
            else:
                _ok, block_msg, warning_msg = _wire_snap.check_splice_compat(picked, self._part)

            if block_msg:
                self._overlay.show_message(mouse_pos, block_msg, blocking=True)
            elif warning_msg:
                self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
            else:
                self._overlay.hide_message()

            self._preview_route_to(self._snap_point(picked))
            return

        self.target.objschematic.set_preview(None)

        xz = self._cursor_xz(mouse_pos)

        reason = None if self._too_short(xz) else self._blocked(xz)
        if reason is None:
            self._overlay.hide_message()
        else:
            self._overlay.show_message(mouse_pos, _BLOCKED_MESSAGES[reason], blocking=True)

        self._ghost_to(xz)

    # ------------------------------------------------------------------
    # Placing waypoints
    # ------------------------------------------------------------------

    @_check_types.do
    def _commit(self, x: float, z: float) -> None:
        point = _wire_reroute.add_waypoint(self.mainframe.project, self.target, x, z, len(self._placed))

        self._points.append(point)
        self._placed.append((x, z))
        self._merged.append(None)

        self.target.objschematic.refresh_waypoints()

    @staticmethod
    def _straight(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
        """Whether ``a -> b -> c`` is one straight horizontal or vertical run,
        so that *b* is not a bend."""
        if abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6:
            return True

        return abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6

    @_check_types.do
    def _place(self, x: float, z: float) -> None:
        """Put a waypoint at ``(x, z)`` -- first taking away the previous one if
        this makes it pointless (see the module docstring)."""
        removed = None

        if self._placed:
            before = self._placed[-2] if len(self._placed) > 1 else self._start_xz

            if self._straight(before, self._placed[-1], (x, z)):
                index = len(self._placed) - 1
                was_locked = index < self._locked

                removed = (self._placed[-1], was_locked)

                row = self._points.pop()
                self._placed.pop()
                self._merged.pop()

                _wire_reroute.remove_waypoint(self.mainframe.project, row)

                if was_locked:
                    self._locked -= 1

        self._commit(x, z)
        self._merged[-1] = removed

    @_check_types.do
    def _click(self, mouse_pos: _point.Point) -> None:
        picked = self._pick_end(mouse_pos)

        if picked is not None:
            self._finish(picked)
            return

        xz = self._cursor_xz(mouse_pos)

        if self._too_short(xz):
            return

        reason = self._blocked(xz)
        if reason is not None:
            self._overlay.show_message(mouse_pos, _BLOCKED_MESSAGES[reason], blocking=True)
            return

        self._place(xz[0], xz[1])
        self.hover(mouse_pos)

    @_check_types.do
    def _undo(self) -> None:
        """Take back the last waypoint the user placed; with none left to take
        back, cancel the wire."""
        if len(self._placed) <= self._locked:
            self.cancel()
            self._finalized = True
            return

        point = self._points.pop()
        self._placed.pop()
        merged = self._merged.pop()

        _wire_reroute.remove_waypoint(self.mainframe.project, point)

        if merged is not None:
            # The click removed the waypoint before it as pointless -- put it back.
            (x, z), was_locked = merged
            self._commit(x, z)

            if was_locked:
                self._locked += 1

        self.target.objschematic.refresh_waypoints()

        if self._last_mouse is not None:
            self.hover(self._last_mouse)

    # ------------------------------------------------------------------
    # Finishing
    # ------------------------------------------------------------------

    @_check_types.do
    def _attach_splice(self, splice_obj: _splice.Splice, end: str) -> None:
        """Attach this wire's *end* ('start' or 'stop') to *splice_obj*'s
        branch point -- sets both 2D and 3D position, same as the
        original handler's own ``_attach_splice``."""
        if end == 'start':
            stale3d_id = self.target.obj3d.start_position.db_id[:-2]
            self.target.obj3d.set_start_position(splice_obj.obj3d.wire_position)
            self.target.db_obj.start_position3d_id = splice_obj.db_obj.branch_position3d_id
            self.target.db_obj.start_position2d_id = splice_obj.db_obj.position2d_id
            self.target.objschematic.set_start_position(splice_obj.db_obj.position2d)
        else:
            stale3d_id = self.target.obj3d.stop_position.db_id[:-2]
            self.target.obj3d.set_stop_position(splice_obj.obj3d.wire_position)
            self.target.db_obj.stop_position3d_id = splice_obj.db_obj.branch_position3d_id
            self.target.db_obj.stop_position2d_id = splice_obj.db_obj.position2d_id
            self.target.objschematic.set_stop_position(splice_obj.db_obj.position2d)

        self.mainframe.project.ptables.pjt_points3d_table[stale3d_id].delete()

        splice_obj.add_wire(self.target)
        self.target.set_sibling(splice_obj, end)
        _wire_reroute.on_wire_attached(self.mainframe.project, self.target)

    @_check_types.do
    def _finish(self, picked) -> None:
        """End the wire on *picked* (a terminal or splice): attach it, and let
        the router lay out everything after the last waypoint the user placed
        -- attaching is what triggers that route, see ``Wire.route_prefix``."""
        if isinstance(picked, _terminal.Terminal):
            ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(picked, self._part)
        else:
            ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(picked, self._part)

        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
            if button == QMessageBox.StandardButton.No:
                return

        project = self.mainframe.project
        ptables = project.ptables

        stale2d_id = self._stop_point2d.db_id

        # The preview overlay (Wire.set_preview) is display-only, never a real
        # waypoint -- the actual route is laid out fresh below, the same way
        # on_wire_attached always does for an auto-routed tail.
        self.target.objschematic.set_preview(None)

        self.target.route_prefix = list(self._placed)

        try:
            if isinstance(picked, _terminal.Terminal):
                stale3d_id = self.target.obj3d.stop_position.db_id[:-2]
                picked.add_wire(self.target, 'stop')
                ptables.pjt_points2d_table[stale2d_id].delete()
                ptables.pjt_points3d_table[stale3d_id].delete()

                if self.target.db_obj.circuit_id is None:
                    self.target.db_obj.circuit_id = picked.db_obj.circuit_id
            else:
                self._attach_splice(picked, 'stop')
                ptables.pjt_points2d_table[stale2d_id].delete()
        finally:
            self.target.route_prefix = None

        self._cleanup()
        self.target.identify(None)
        project.add_wire(self.target)

        self._finalized = True

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    @_check_types.do
    def _cleanup(self) -> None:
        self._set_hover(None)

        if self.target is not None:
            self.target.objschematic.set_preview(None)

        if self._overlay is not None:
            self._overlay.hide_message()
            self._overlay.deleteLater()
            self._overlay = None

    @_check_types.do
    def cancel(self) -> None:
        project = self.mainframe.project

        for point in reversed(self._points):
            _wire_reroute.remove_waypoint(project, point)

        self._points = []
        self._placed = []

        self._cleanup()

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
