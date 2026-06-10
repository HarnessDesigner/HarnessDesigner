# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore
import os


class PathCtrl(QtWidgets.QWidget):
    """
    Text field + browse button that emits path_changed(str).
    """

    pathChanged: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self, parent, path, wildcard='', http_browse=True):
        """
        Initialise the :class:`PathCtrl` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param path: Filesystem path.
        :type path: UNKNOWN
        :param wildcard: Value for ``wildcard``.
        :type wildcard: UNKNOWN
        :param http_browse: Value for ``http_browse``.
        :type http_browse: UNKNOWN
        """

        super().__init__(parent)

        self._path = path
        self._wildcard = wildcard
        self._http_browse = http_browse

        self.path_ctrl = QtWidgets.QLineEdit(path, self)
        self.path_button = QtWidgets.QPushButton('...', self)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.path_ctrl, stretch=1)
        row.addWidget(self.path_button)

        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(row)
        self.setLayout(outer)

        self.path_button.clicked.connect(self.on_open_file)
        self.path_ctrl.returnPressed.connect(self._on_enter)

    def GetValue(self) -> str:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """

        return self._path

    def SetValue(self, value: str):
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: str
        """

        self._path = value
        self.path_ctrl.blockSignals(True)

        self.path_ctrl.setText(value)

        self.path_ctrl.blockSignals(False)

    def SetWildcards(self, value: str):
        """
        Execute the set wildcards operation.

        :param value: Value to store or process.
        :type value: str
        """

        self._wildcard = value

    def on_open_file(self):
        """
        Handle the open file event.
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

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, '', default_dir, self._wildcard)

        if path and path != self._path:
            self._path = path
            self.path_ctrl.setText(path)
            self.pathChanged.emit(path)

    def _on_enter(self):
        """
        Handle the enter event.
        """

        path = self.path_ctrl.text()
        if path == self._path:
            return
        self._path = path

        self.pathChanged.emit(path)
