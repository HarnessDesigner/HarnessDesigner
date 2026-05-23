from typing import cast

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui


class EditableTabBar(QtWidgets.QTabBar):
    # index, old_name, new_name, widget
    tabRenamed: QtCore.SignalInstance = (
        QtCore.Signal(int, str, str, QtWidgets.QWidget))

    # index, name, widget
    tabDeleteRequested: QtCore.SignalInstance = (
        QtCore.Signal(int, str, QtWidgets.QWidget))

    # new tab index (last + 1)
    tabAddRequested: QtCore.SignalInstance = QtCore.Signal(int)

    def __init__(self, parent: "EditableTabCtrl"):
        self._tab_widget = parent
        super().__init__(parent)
        self._editor = QtWidgets.QLineEdit(self)
        self._editor.setWindowFlags(QtCore.Qt.WindowType.Popup)
        self._editor.hide()
        self._editor.editingFinished.connect(self._finish_editing)
        self._editing_index = -1

        if parent.tab_bar_tooltip:
            self.setToolTip(parent.tab_bar_tooltip)

    def contextMenuEvent(self, event):
        index = self.tabAt(event.pos())

        menu = QtWidgets.QMenu(self)

        if index < 0 and self._tab_widget.add_tab_label:
            action = QtGui.QAction(self._tab_widget.add_tab_label, self)
            action.triggered.connect(
                lambda checked=False, i=index: self._request_add(i)
            )

            menu.addAction(action)
        elif index > 0:
            if self._tab_widget.rename_tab_label:
                action = QtGui.QAction(self._tab_widget.rename_tab_label, self)
                action.triggered.connect(
                    lambda checked=False, i=index: self._start_editing(i))

                menu.addAction(action)

                if (
                    self._tab_widget.add_tab_label or
                    self._tab_widget.delete_tab_label
                ):
                    menu.addSeparator()

            if self._tab_widget.add_tab_label:
                action = QtGui.QAction(self._tab_widget.add_tab_label, self)
                action.triggered.connect(
                    lambda checked=False, i=index: self._request_add(i))

                menu.addAction(action)

            if self._tab_widget.delete_tab_label:
                action = QtGui.QAction(self._tab_widget.delete_tab_label, self)
                action.triggered.connect(
                    lambda checked=False, i=index: self._request_delete(i))

                menu.addAction(action)

        menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            self._start_editing(index)

    def _start_editing(self, index):
        self._editing_index = index
        rect = self.tabRect(index)
        self._editor.setGeometry(rect)
        self._editor.setText(self.tabText(index))
        self._editor.selectAll()
        self._editor.show()
        self._editor.setFocus()

    def _finish_editing(self):
        if self._editing_index >= 0:
            old_name = self.tabText(self._editing_index)
            new_name = self._editor.text()
            tab_widget = cast(QtWidgets.QTabWidget, self.parent())
            widget = tab_widget.widget(self._editing_index)
            self.setTabText(self._editing_index, new_name)
            self.tabRenamed.emit(self._editing_index, old_name, new_name, widget)
            self._editing_index = -1
        self._editor.hide()

    def _request_delete(self, index):
        tab_widget = cast(QtWidgets.QTabWidget, self.parent())
        name = self.tabText(index)
        widget = tab_widget.widget(index)
        self.tabDeleteRequested.emit(index, name, widget)

    def _request_add(self, _):
        tab_widget = cast(QtWidgets.QTabWidget, self.parent())
        new_index = tab_widget.count()
        self.tabAddRequested.emit(new_index)


class EditableTabCtrl(QtWidgets.QTabWidget):
    # index, old_name, new_name, widget
    tabRenamed: QtCore.SignalInstance = (
        QtCore.Signal(int, str, str, QtWidgets.QWidget))

    # index, name, widget
    tabDeleteRequested: QtCore.SignalInstance = (
        QtCore.Signal(int, str, QtWidgets.QWidget))

    # new tab index
    tabAddRequested: QtCore.SignalInstance = QtCore.Signal(int)

    # override these class attributes to alter the labels
    # used in the context menu for the tabs
    rename_tab_label = 'Rename Tab'
    add_tab_label = 'Add Tab'
    delete_tab_label = 'Delete Tab'

    # override this attribute to set a custom tooltip for the tab bar
    tab_bar_tooltip = None

    def __init__(self, parent=None):
        super().__init__(parent)
        tab_bar = EditableTabBar(self)
        tab_bar.tabRenamed.connect(self.tabRenamed)
        tab_bar.tabDeleteRequested.connect(self.tabDeleteRequested)
        tab_bar.tabAddRequested.connect(self.tabAddRequested)
        self.setTabBar(tab_bar)
