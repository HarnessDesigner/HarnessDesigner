# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6 import QtWidgets


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class EditorObj:

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = EditorObjPanel(mainframe)
        self.mainframe = mainframe

        self._dock = mainframe._make_dock(
            title='Object Editor',
            name='editor_obj',
            widget=self.editor,
            area=Qt.DockWidgetArea.RightDockWidgetArea,
        )
        # self._dock.visibilityChanged.connect(self._on_visibility_changed)
        self._dock.show()

    def _on_visibility_changed(self, visible):
        if not visible:
            self.set_selected(None)

    def Show(self, show=True):
        if show:
            self.set_selected(self.mainframe.get_selected())
            self._dock.show()
            self._dock.raise_()
        else:
            self.set_selected(None)
            self._dock.hide()

    def IsShown(self):
        return self._dock.isVisible()

    def Refresh(self, *args, **kwargs):
        self.editor.update()

    def Destroy(self):
        self.editor.deleteLater()

    def set_selected(self, obj):
        if self.IsShown():
            self.editor.set_selected(obj)


class EditorObjPanel(QWidget):

    def __init__(self, parent: "_mainframe.MainFrame"):
        QWidget.__init__(self, parent)
        self.mainframe = parent
        self.control = None

        vsizer = QVBoxLayout(self)
        hsizer = QHBoxLayout()
        vsizer.addLayout(hsizer)

        self.sizer = hsizer
        self._selected = None

    def set_selected(self, obj):
        if obj is None:
            if self.control is not None:
                self.control.hide()
                self.sizer.removeWidget(self.control)
                self.control.setParent(self.mainframe)
                self.control = None
        else:
            control = obj.db_obj.table.control
            control.set_obj(obj.db_obj)
            control.setParent(self)

            if self.control is not None:
                self.control.hide()
                self.sizer.removeWidget(self.control)
                self.control.setParent(self.mainframe)

            self.sizer.addWidget(control, 1)
            # Qt does not have wx.EXPAND|wx.ALL; margins go on the layout
            self.sizer.setContentsMargins(10, 10, 10, 10)
            self.control = control
            control.show()

        self.updateGeometry()
        self.update()

        self._selected = obj
