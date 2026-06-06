# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore

from . import editor_widget as _editor_widget

if TYPE_CHECKING:
    from ... import ui as _ui


class EditorCircuit:
    """
    Wrapper that creates the dock widget and owns the EditorCircuitPanel.

    In the wx version this subclassed aui.AuiPaneInfo and registered
    itself with the AuiManager directly. In Qt, dock management belongs
    to QMainWindow (Phase 2). EditorCircuit now acts as a thin coordinator
    that holds the panel and exposes the same public surface.
    """

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`EditorCircuit` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        self.mainframe = mainframe
        self.editor = EditorCircuitPanel(mainframe)

        # The dock widget itself is created and registered by mainframe
        # via mainframe._make_dock('Database Editor', 'editor_db', self.editor, Bottom).
        # EditorDB just stores the reference so callers can reach the panel.

        self._dock = mainframe._make_dock(  # NOQA
            title='Circuit Editor',
            name='editor_circuit',
            widget=self.editor,
            area=QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        # self._dock.visibilityChanged.connect(self._on_visibility_changed)
        self._dock.show()

    def Show(self, show=True):
        """Execute the show operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param show: Value for ``show``.
        :type show: UNKNOWN
        """
        self.editor.setVisible(show)

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.editor.Refresh()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.editor.deleteLater()


class EditorCircuitPanel(_editor_widget.EditorCircuitPanel):
    """Represent an editor circuit panel in :mod:`harness_designer.ui.editor_ciruit.editor_circuit`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_ui.MainFrame"):
        """Initialise the :class:`EditorCircuitPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        """
        super().__init__(parent)

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.update()
