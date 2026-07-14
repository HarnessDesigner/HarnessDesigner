# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .. import dock_base as _dock_base

if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class EditorAssembly(_dock_base.DockBase):
    """
    Represent an editor assembly in :mod:`harness_designer.ui.editor_assembly.editor_assembly`.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`EditorAssembly` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = EditorAssemblyPanel(mainframe)

        super().__init__(mainframe, 'Assembly Editor', 'editor_assembly',
                         Qt.DockWidgetArea.LeftDockWidgetArea)

    @property
    def editor(self) -> "EditorAssemblyPanel":
        return self._ui_obj


class EditorAssemblyPanel(QWidget):
    """
    Represent an editor assembly panel in :mod:`harness_designer.ui.editor_assembly.editor_assembly`.
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        """
        Initialise the :class:`EditorAssemblyPanel` instance.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
        """

        QWidget.__init__(self, parent)
        self.mainframe = parent
