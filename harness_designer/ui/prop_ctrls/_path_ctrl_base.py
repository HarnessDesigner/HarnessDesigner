# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog
from PySide6.QtCore import Signal


class PathEvent:

    def __init__(self, value):
        self._value = value

    def GetValue(self):
        return self._value

    def SetValue(self, v):
        self._value = v


class PathCtrl(QWidget):
    """Text field + browse button that emits path_changed(str)."""

    path_changed = Signal(str)

    def __init__(self, parent, path, wildcard='', http_browse=True):
        QWidget.__init__(self, parent)
        self._path = path
        self._wildcard = wildcard
        self._http_browse = http_browse

        self.path_ctrl = QLineEdit(path, self)
        self.path_button = QPushButton('...', self)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.path_ctrl, stretch=1)
        row.addWidget(self.path_button)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(row)
        self.setLayout(outer)

        self.path_button.clicked.connect(self.on_open_file)
        self.path_ctrl.returnPressed.connect(self._on_enter)

    def GetValue(self) -> str:
        return self._path

    def SetValue(self, value: str):
        self._path = value
        self.path_ctrl.blockSignals(True)
        self.path_ctrl.setText(value)
        self.path_ctrl.blockSignals(False)

    def SetWildcards(self, value: str):
        self._wildcard = value

    def on_open_file(self):
        value = self.path_ctrl.text()

        if not value or (not self._http_browse and value.startswith('http')):
            default_dir = os.path.expandvars('~')
            default_file = ''
        else:
            default_dir, default_file = os.path.split(value)
            if not os.path.exists(value):
                default_file = ''
                if not os.path.exists(default_dir):
                    default_dir = os.path.expandvars('~')

        path, _ = QFileDialog.getOpenFileName(
            self, '', default_dir, self._wildcard)

        if path and path != self._path:
            self._path = path
            self.path_ctrl.setText(path)
            self.path_changed.emit(path)

    def _on_enter(self):
        path = self.path_ctrl.text()
        if path == self._path:
            return
        self._path = path
        self.path_changed.emit(path)
