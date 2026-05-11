# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout

from . import prop_base as _prop_base
from ._path_ctrl_base import PathCtrl
from ... import utils as _utils


class Model3DProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label)
        self._value = ''
        self._file_types = {}

        self._st = QLabel(label + ':', self)
        self._ctrl = PathCtrl(self, '', wildcard=_utils.MODEL_FILE_WILDCARDS)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)
        row.addWidget(self._ctrl, stretch=1)
        self._sizer.addLayout(row)

        self._ctrl.path_changed.connect(self._on_path_changed)

    def SetFileTypes(self, file_types):
        self._file_types = file_types

    def _on_path_changed(self, path):
        if path == self._value:
            return
        self._value = path
        self._send_changed_event(str, path)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._value = value
        self._ctrl.SetValue(value)
