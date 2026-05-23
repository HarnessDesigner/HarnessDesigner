# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout

from . import prop_base as _prop_base
from ._path_ctrl_base import PathCtrl
from ... import utils as _utils


class Model3DProperty(_prop_base.Property):
    """Represent a model 3dproperty in :mod:`harness_designer.ui.prop_ctrls.model3d_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`Model3DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
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
        """Execute the set file types operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param file_types: Value for ``file_types``.
        :type file_types: UNKNOWN
        """
        self._file_types = file_types

    def _on_path_changed(self, path):
        """Handle the path changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: UNKNOWN
        """
        if path == self._value:
            return
        self._value = path
        self._send_changed_event(str, path)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._value

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._value = value
        self._ctrl.SetValue(value)
