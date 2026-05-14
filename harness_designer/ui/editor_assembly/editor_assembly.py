# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6 import QtWidgets


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class EditorAssembly:

    def __init__(self, mainframe: "_mainframe.MainFrame"):
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
        if show:
            self._dock.show()
            self._dock.raise_()
        else:
            self._dock.hide()

    def Refresh(self, *args, **kwargs):
        self.editor.update()

    def Destroy(self):
        self.editor.deleteLater()


class EditorAssemblyPanel(QWidget):

    def __init__(self, parent: "_mainframe.MainFrame"):
        QWidget.__init__(self, parent)
        self.mainframe = parent
