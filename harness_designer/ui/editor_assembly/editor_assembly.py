# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6 import QtWidgets


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class EditorAssembly:
    """Represent an editor assembly in :mod:`harness_designer.ui.editor_assembly.editor_assembly`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`EditorAssembly` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """
        self.editor = EditorAssemblyPanel(mainframe)
        self.mainframe = mainframe

        dock = mainframe._make_dock(
            title='Assembly Editor',
            name='editor_assembly',
            widget=self.editor,
            area=Qt.RightDockWidgetArea,
        )
        self._dock = dock
        dock.show()

    def Show(self, show=True):
        """Execute the show operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param show: Value for ``show``.
        :type show: UNKNOWN
        """
        if show:
            self._dock.show()
            self._dock.raise_()
        else:
            self._dock.hide()

    def Refresh(self, *args, **kwargs):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        self.editor.update()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.editor.deleteLater()


class EditorAssemblyPanel(QWidget):
    """Represent an editor assembly panel in :mod:`harness_designer.ui.editor_assembly.editor_assembly`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        """Initialise the :class:`EditorAssemblyPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
        """
        QWidget.__init__(self, parent)
        self.mainframe = parent
