# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Context menus shown when a view is right clicked over empty space.

The position of that right click (a canvas-local :class:`Point`, the same
kind every mouse event carries) is where whatever the chosen action adds
goes. Every action is deferred one event-loop tick, past the menu closing,
since most of them open a modal part-search dialog first.
"""

from typing import TYPE_CHECKING
from collections.abc import Callable

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...geometry import point as _point
    from ... import ui as _ui


class _EmptySpaceMenu(QtWidgets.QMenu):
    """Shared shell: holds the mainframe and the right-click position."""

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", mouse_pos: "_point.Point") -> None:
        QtWidgets.QMenu.__init__(self)
        self.mainframe = mainframe
        self.mouse_pos = mouse_pos

    @_check_types.do
    def _add_action(self, text: str, callback: Callable[[], None]) -> QtGui.QAction:
        """Add an action that runs *callback* one tick after the menu closes."""

        @_check_types.do
        def _triggered() -> None:
            QtCore.QTimer.singleShot(0, callback)

        action = self.addAction(text)
        action.triggered.connect(_triggered)

        return action


class EmptySpaceMenu3D(_EmptySpaceMenu):
    """3D view: Add Wire / Terminal / Housing / Project Model."""

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", mouse_pos: "_point.Point") -> None:
        super().__init__(mainframe, mouse_pos)

        self._add_action('Add Wire', self.on_add_wire)
        self._add_action('Add Terminal', self.on_add_terminal)
        self._add_action('Add Housing', self.on_add_housing)
        self.addSeparator()

        if mainframe.project.db_obj.model is None:
            text = 'Add Project Model'
        else:
            text = 'Edit Project Model'

        self._add_action(text, self.on_add_project_model)

    @_check_types.do
    def on_add_wire(self) -> None:
        from ...objects.objects_3d import wire as _wire_3d

        _wire_3d.Wire.start_add(self.mainframe, mouse_pos=self.mouse_pos)

    @_check_types.do
    def on_add_terminal(self) -> None:
        from ...objects.objects_3d import terminal as _terminal_3d

        _terminal_3d.Terminal.add_free(self.mainframe, '3d', self.mouse_pos)

    @_check_types.do
    def on_add_housing(self) -> None:
        from ...objects.objects_3d import housing as _housing_3d

        _housing_3d.Housing.start_add(self.mainframe, mouse_pos=self.mouse_pos)

    @_check_types.do
    def on_add_project_model(self) -> None:
        from ..dialogs import project_model_dialog as _project_model_dialog

        project = self.mainframe.project

        dlg = _project_model_dialog.ProjectModelDialog(self.mainframe, project.db_obj)

        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            path, color_id = dlg.GetValue()

            if path:
                project.set_project_model(path, color_id)

        dlg.deleteLater()


class EmptySpaceMenuPegboard(_EmptySpaceMenu):
    """Peg-board view: Add Wire / Terminal / Housing."""

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", mouse_pos: "_point.Point") -> None:
        super().__init__(mainframe, mouse_pos)

        self._add_action('Add Wire', self.on_add_wire)
        self._add_action('Add Terminal', self.on_add_terminal)
        self._add_action('Add Housing', self.on_add_housing)

    @_check_types.do
    def on_add_wire(self) -> None:
        from ...objects.objects_pegboard import wire as _wire_pegboard

        _wire_pegboard.Wire.start_add(self.mainframe, mouse_pos=self.mouse_pos)

    @_check_types.do
    def on_add_terminal(self) -> None:
        from ...objects.objects_3d import terminal as _terminal_3d

        _terminal_3d.Terminal.add_free(self.mainframe, 'pegboard', self.mouse_pos)

    @_check_types.do
    def on_add_housing(self) -> None:
        from ...objects.objects_pegboard import housing as _housing_pegboard

        _housing_pegboard.Housing.start_add(self.mainframe, mouse_pos=self.mouse_pos)


class EmptySpaceMenuSchematic(_EmptySpaceMenu):
    """Schematic view: Add Terminal / Housing."""

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", mouse_pos: "_point.Point") -> None:
        super().__init__(mainframe, mouse_pos)

        # A free-standing terminal has no schematic drawing yet (a cavity-less
        # terminal has no stub/name box to be drawn from) -- shown, but off,
        # until that visual is designed.
        action = self._add_action('Add Terminal', self.on_add_terminal)
        action.setEnabled(False)
        action.setToolTip('Free-standing terminals are not drawn in the schematic yet')

        self._add_action('Add Housing', self.on_add_housing)

    @_check_types.do
    def on_add_terminal(self) -> None:
        pass

    @_check_types.do
    def on_add_housing(self) -> None:
        from ...objects.objects_schematic import housing as _housing_schematic

        _housing_schematic.Housing.start_add(self.mainframe, mouse_pos=self.mouse_pos)
