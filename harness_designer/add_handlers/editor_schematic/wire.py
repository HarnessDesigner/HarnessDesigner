# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Terminal/splice-pinned wire placement for the schematic editor.

Ported from ``handlers.wire_handler_2d.AddWireHandler2D`` -- unlike the
3D editor's Wire add-handler, the schematic editor has no free-space
drawing tool at all: every session starts pinned to a Terminal or
Splice (the real ``Wire`` facade is built synchronously in
``objects.objects_schematic.wire.Wire.start_add``, so there is no
placeholder-preview phase here either), and the path between the two
ends is always auto-routed (``objects_schematic.wire_routing``), never
hand-drawn -- the live preview during hover is just a straight line to
the cursor, real orthogonal geometry only gets computed once, on the
second click.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...handlers import wire_snap as _wire_snap
from ...geometry import point as _point
from ...objects import terminal as _terminal
from ...objects import splice as _splice
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


class Wire(_base.AddHandlerBase):
    """Terminal/splice-pinned wire placement -- see the module docstring."""

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

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.objschematic

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
        world_pos = self.camera.screen_to_world(mouse_pos)

        stop = self._stop_point2d.point
        with stop:
            stop.x = world_pos.x
            stop.z = world_pos.z

        self.mainframe.editor2d.Refresh(False)

    @_check_types.do
    def _attach_splice(self, splice_obj: "_splice.Splice", end: str) -> None:
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

    @_check_types.do
    def _route(self) -> None:
        """Auto-route this now-fully-connected wire's 2D path."""
        from ...objects.objects_schematic import wire_routing as _wire_routing

        ptables = self.mainframe.project.ptables

        start = self.target.db_obj.start_position2d
        stop = self.target.db_obj.stop_position2d

        waypoints = _wire_routing.route(
            self.mainframe.project, (float(start.x), float(start.z)),
            (float(stop.x), float(stop.z)), ignore_wire=self.target)

        for i, (x, z) in enumerate(waypoints):
            ptables.pjt_points2d_table.insert(
                x, z, wire_id=self.target.db_obj.db_id, idx=i)

        if waypoints:
            self.target.objschematic.refresh_waypoints()

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        picked = _object_picker.find_object(
            mouse_pos, self.mainframe.editor2d.editor.objects,
            self.camera, self._get_view_object)

        if picked is self.target or picked is None:
            return

        ptables = self.mainframe.project.ptables

        if isinstance(picked, _terminal.Terminal):
            if picked is self._start_obj:
                return

            ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(picked, self._part)
            if not ok:
                block_msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(self.mainframe, 'Incompatible Wire', block_msg)
                if button == QMessageBox.StandardButton.No:
                    return

            stale2d_id = self._stop_point2d.db_id
            stale3d_id = self.target.obj3d.stop_position.db_id[:-2]
            picked.add_wire(self.target, 'stop')
            ptables.pjt_points2d_table[stale2d_id].delete()
            ptables.pjt_points3d_table[stale3d_id].delete()

            if self.target.db_obj.circuit_id is None:
                self.target.db_obj.circuit_id = picked.db_obj.circuit_id

        elif isinstance(picked, _splice.Splice):
            if picked is self._start_obj:
                return

            stale2d_id = self._stop_point2d.db_id
            self._attach_splice(picked, 'stop')
            ptables.pjt_points2d_table[stale2d_id].delete()

        else:
            return

        self._route()
        self.target.identify(None)
        self.mainframe.project.add_wire(self.target)

        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
