# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout

from . import prop_base as _prop_base
from ._path_ctrl_base import PathCtrl
from ._image_ctrl_base import ImageCtrl
from ... import utils as _utils


class DatasheetCADProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label)
        self._value = ''
        self._file_types = {}
        self._save_path = None

        self._st = QLabel(label + ':', self)
        self._ctrl = PathCtrl(self, '', wildcard=_utils.IMAGE_FILE_WILDCARDS)
        self._image = ImageCtrl(self, {}, '', None, support_pdf=True)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(5, 2, 5, 2)
        top_row.addWidget(self._st)
        top_row.addWidget(self._ctrl, stretch=1)
        self._sizer.addLayout(top_row)

        img_row = QHBoxLayout()
        img_row.setContentsMargins(5, 2, 5, 2)
        img_row.addWidget(self._image, stretch=1)
        self._sizer.addLayout(img_row)

        self._ctrl.path_changed.connect(self._on_path_changed)

    def SetFileTypes(self, file_types):
        self._file_types = file_types
        self._image.SetFileTypes(file_types)

    def _on_path_changed(self, path):
        if path == self._value:
            return
        if self._image.SetValue(path):
            self._value = path
            self._send_changed_event(str, path)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value):
        self._value = value[0]
        self._save_path = value[1]
        if value[1] is None:
            self._image.SetValue(value[0])
        else:
            self._image.SetValue(value[1])
        self._ctrl.SetValue(value[0])
