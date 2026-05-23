# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog
from PySide6.QtCore import Signal


class PathEvent:
    """Represent a path event in :mod:`harness_designer.ui.prop_ctrls._path_ctrl_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, value):
        """Initialise the :class:`PathEvent` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._value = value

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._value

    def SetValue(self, v):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param v: Value for ``v``.
        :type v: UNKNOWN
        """
        self._value = v


class PathCtrl(QWidget):
    """Text field + browse button that emits path_changed(str)."""

    path_changed = Signal(str)

    def __init__(self, parent, path, wildcard='', http_browse=True):
        """Initialise the :class:`PathCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param path: Filesystem path.
        :type path: UNKNOWN
        :param wildcard: Value for ``wildcard``.
        :type wildcard: UNKNOWN
        :param http_browse: Value for ``http_browse``.
        :type http_browse: UNKNOWN
        """
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
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._path

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._path = value
        self.path_ctrl.blockSignals(True)
        self.path_ctrl.setText(value)
        self.path_ctrl.blockSignals(False)

    def SetWildcards(self, value: str):
        """Execute the set wildcards operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._wildcard = value

    def on_open_file(self):
        """Handle the open file event.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
        """Handle the enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        path = self.path_ctrl.text()
        if path == self._path:
            return
        self._path = path
        self.path_changed.emit(path)
