# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler for drawing a wire from the 2D schematic editor.

Started from a Terminal's or Splice's own "Add Wire" context-menu action
(see ``objects2d/terminal.py``'s ``TerminalMenu.on_add_wire``) -- pinned
to that terminal/splice immediately, so unlike ``handlers/wire_handler.py``'s
3D ``AddWireHandler`` there's no free first-click phase: the schematic
editor doesn't have a free-space wire-drawing tool, only Terminal/Splice
targets, since the path between them is always auto-routed (see
``objects2d/wire_routing.py``), never hand-drawn.

A live straight-line preview tracks the mouse (mirrors ``AddWireHandler``'s
own preview, which is likewise a straight line during the drag -- the
real orthogonal geometry is only computed once, at the second click) until
that second click lands on a compatible Terminal or Splice, which
finishes the connection at both ends -- in both editors at once, since
``Terminal.add_wire``/the splice-attach sequence below set 2D *and* 3D
position in one call (see ``objects/terminal.py``, and
``handlers/wire_handler.py``'s own splice branch, which this mirrors) --
and runs the auto-router to lay out the final 2D path.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from . import handler_base as _handler_base
from .wire_handler import _get_terminal_compat_pns, _check_terminal_compat
from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import terminal as _terminal
from ..objects import splice as _splice
from ..objects import wire as _wire
from ..objects.objects2d import wire_routing as _wire_routing
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui


@_check_types.do
def _choose_part(mainframe, initial_results=None):
    """Run the wire part-search dialog, returning the chosen part id (or
    ``None`` if cancelled)."""
    dlg = _part_search.SearchDialog(
        mainframe, _editor_db.WiresPage, title='Add Wire',
        table=mainframe.global_db.wires_table, initial_results=initial_results)

    part_id = dlg.GetValue() if dlg.exec() == QDialog.DialogCode.Accepted else None
    dlg.deleteLater()

    return part_id


class AddWireHandler2D(_handler_base.HandlerBase):
    """Two-endpoint interactive wire placement, driven by the 2D
    schematic editor's own mouse events -- ``ui/mainframe.py``'s
    ``_on_*_2d`` dispatch drives any active ``_obj_handler`` identically
    regardless of which editor started it, so no new event plumbing is
    needed here.
    """

    obj: _wire.Wire = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 terminal: _terminal.Terminal = None,
                 splice: _splice.Splice = None):
        super().__init__(mainframe, None)

        # HandlerBase.__init__ defaults self.camera to the 3D camera --
        # every position this handler deals with is a 2D schematic
        # point, so it needs the 2D camera instead.
        self.camera = self.mainframe.editor2d.editor.camera

        start = terminal if terminal is not None else splice
        if start is None:
            self._finalized = True
            return

        if terminal is not None:
            compat_pns = _get_terminal_compat_pns(mainframe, terminal)
            part_id = _choose_part(mainframe, initial_results=compat_pns)
        else:
            part_id = _choose_part(mainframe)

        if part_id is None:
            self._finalized = True
            return

        self.part_id = part_id
        self.part = mainframe.global_db.wires_table[part_id]

        start_circuit_id = None
        if terminal is not None:
            ok, msg = _check_terminal_compat(terminal, self.part)
            if not ok:
                msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(mainframe, 'Incompatible Wire', msg)
                if button == QMessageBox.StandardButton.No:
                    self._finalized = True
                    return

            start_circuit_id = terminal.db_obj.circuit_id

        ptables = self.ptables

        # Placeholder 3D points -- overwritten immediately below by the
        # start attach, and tracked live during hover for the stop, same
        # two-placeholder shape handlers/wire_handler.py's own
        # _start_from_terminal uses (never sharing one point row between
        # start and stop -- Point identity is a singleton keyed by db_id,
        # so two ends sharing a row would move together).
        start3d = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        if terminal is not None:
            initial_pos = terminal.db_obj.attach_position3d
        else:
            initial_pos = splice.obj3d.wire_position

        stop3d = ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        start_pos2d = start.db_obj.position2d
        stop2d = ptables.pjt_points2d_table.insert(float(start_pos2d.x), float(start_pos2d.z))
        self._stop_point2d = stop2d

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, start_circuit_id,
            start3d.db_id, stop3d.db_id,
            None, stop2d.db_id,
            True, False, None, None, False)

        self.obj = _wire.Wire(mainframe, wire_db)

        if terminal is not None:
            attached = terminal.add_wire(self.obj, 'start')
            # terminal.add_wire (unlike _attach_splice below) leaves the
            # stale placeholder for the caller to clean up -- matches
            # handlers/wire_handler.py's own _start_from_terminal.
            if attached:
                ptables.pjt_points3d_table[start3d.db_id].delete()
        else:
            # _attach_splice always succeeds (no compatibility check for
            # splices, same as the 3D handler) and deletes the stale
            # placeholder itself.
            attached = self._attach_splice(splice, 'start')

        if not attached:
            self.obj.delete()
            self.obj = None
            ptables.pjt_points3d_table[start3d.db_id].delete()
            QMessageBox.warning(
                mainframe, 'Incompatible Wire',
                'This wire is no longer compatible with the terminal.')
            self._finalized = True
            return

        self._start_obj = start

    @_check_types.do
    def _attach_splice(self, splice_obj: _splice.Splice, end: str) -> bool:
        """Attach this wire's *end* ('start' or 'stop') to *splice_obj*'s
        branch point -- mirrors ``handlers/wire_handler.py``'s own
        splice-attach sequence (there's no generic
        ``Splice.add_wire``-does-everything method the way
        ``Terminal.add_wire`` is; the position-setting lives in the
        caller on both the 3D and 2D sides), setting both 2D and 3D
        position so the connection is valid in either editor.
        """
        if end == 'start':
            stale3d_id = self.obj.obj3d.start_position.db_id[:-2]
            self.obj.obj3d.set_start_position(splice_obj.obj3d.wire_position)
            self.obj.db_obj.start_position3d_id = splice_obj.db_obj.branch_position3d_id
            self.obj.db_obj.start_position2d_id = splice_obj.db_obj.position2d_id
            self.obj.obj2d.set_start_position(splice_obj.db_obj.position2d)
        else:
            stale3d_id = self.obj.obj3d.stop_position.db_id[:-2]
            self.obj.obj3d.set_stop_position(splice_obj.obj3d.wire_position)
            self.obj.db_obj.stop_position3d_id = splice_obj.db_obj.branch_position3d_id
            self.obj.db_obj.stop_position2d_id = splice_obj.db_obj.position2d_id
            self.obj.obj2d.set_stop_position(splice_obj.db_obj.position2d)

        self.ptables.pjt_points3d_table[stale3d_id].delete()

        splice_obj.add_wire(self.obj)
        self.obj.set_sibling(splice_obj, end)

        return True

    @_check_types.do
    def hover(self, mouse_pos: _point.Point):
        if self._finalized or self.obj is None:
            return

        world_pos = self.camera.screen_to_world(mouse_pos)

        stop = self._stop_point2d.point
        with stop:
            stop.x = world_pos.x
            stop.z = world_pos.z

        self.mainframe.editor2d.Refresh(False)

    @_check_types.do
    def release_capture(self):
        if self._finalized or self._captured_position is None:
            return

        mouse_pos = self._captured_position
        picked = _object_picker.find_object(
            mouse_pos, self.mainframe.editor2d.editor.objects, self.camera, attr='obj2d')

        if picked is self.obj or picked is None:
            return

        if isinstance(picked, _terminal.Terminal):
            if picked is self._start_obj:
                return

            ok, msg = _check_terminal_compat(picked, self.part)
            if not ok:
                msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(self.mainframe, 'Incompatible Wire', msg)
                if button == QMessageBox.StandardButton.No:
                    return

            stale2d_id = self._stop_point2d.db_id
            stale3d_id = self.obj.obj3d.stop_position.db_id[:-2]
            picked.add_wire(self.obj, 'stop')
            self.ptables.pjt_points2d_table[stale2d_id].delete()
            self.ptables.pjt_points3d_table[stale3d_id].delete()

            if self.obj.db_obj.circuit_id is None:
                self.obj.db_obj.circuit_id = picked.db_obj.circuit_id

        elif isinstance(picked, _splice.Splice):
            if picked is self._start_obj:
                return

            stale2d_id = self._stop_point2d.db_id
            self._attach_splice(picked, 'stop')
            self.ptables.pjt_points2d_table[stale2d_id].delete()

        else:
            return

        self._route()
        self.obj.identify(None)
        self.mainframe.project.add_wire(self.obj)

        self._finalized = True

    @_check_types.do
    def _route(self):
        """Auto-route this now-fully-connected wire's 2D path -- see
        ``objects2d/wire_routing.py``.
        """
        start = self.obj.db_obj.start_position2d
        stop = self.obj.db_obj.stop_position2d

        waypoints = _wire_routing.route(
            self.mainframe.project, (float(start.x), float(start.z)),
            (float(stop.x), float(stop.z)), ignore_wire=self.obj)

        for i, (x, z) in enumerate(waypoints):
            self.ptables.pjt_points2d_table.insert(
                x, z, wire_id=self.obj.db_obj.db_id, idx=i)

        if waypoints:
            self.obj.obj2d.refresh_waypoints()

    @_check_types.do
    def cancel(self):
        if self.obj is not None:
            self.obj.delete()
            self.obj = None

        self._finalized = True
