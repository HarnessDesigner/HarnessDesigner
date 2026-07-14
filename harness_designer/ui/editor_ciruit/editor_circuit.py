# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore

from . import editor_widget as _editor_widget
from .. import dock_base as _dock_base

if TYPE_CHECKING:
    from ... import ui as _ui


class EditorCircuit(_dock_base.DockBase):
    """
    Wrapper that creates the dock widget and owns the EditorCircuitPanel.

    In the wx version this subclassed aui.AuiPaneInfo and registered
    itself with the AuiManager directly. In Qt, dock management belongs
    to QMainWindow (Phase 2). EditorCircuit now acts as a thin coordinator
    that holds the panel and exposes the same public surface.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """
        Initialise the :class:`EditorCircuit` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        self._ui_obj = EditorCircuitPanel(mainframe)

        super().__init__(mainframe, 'Circuit Editor', 'editor_circuit',
                         QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

    @property
    def editor(self) -> "EditorCircuitPanel":
        return self._ui_obj


class EditorCircuitPanel(_editor_widget.EditorCircuitPanel):
    """
    Represent an editor circuit panel in :mod:`harness_designer.ui.editor_ciruit.editor_circuit`.
    """

    def __init__(self, parent: "_ui.MainFrame"):
        """
        Initialise the :class:`EditorCircuitPanel` instance.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        """

        super().__init__(parent)

    def Refresh(self, *_, **__):
        """
        Execute the refresh operation.

        :param _: Value for ``_``.
        :type _: UNKNOWN

        :param __: Value for ``__``.
        :type __: UNKNOWN
        """

        self.update()
