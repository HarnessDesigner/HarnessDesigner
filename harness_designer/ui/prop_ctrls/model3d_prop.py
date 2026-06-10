# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from ._path_ctrl_base import PathCtrl
from ... import utils as _utils
from . import events as _events


class Model3DProperty(QtWidgets.QWidget):
    """Represent a model 3dproperty in :mod:`harness_designer.ui.prop_ctrls.model3d_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str):
        """Initialise the :class:`Model3DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        """

        super().__init__(parent)

        self._value = ''
        self._file_types = {}
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = PathCtrl(self, '', wildcard=_utils.MODEL_FILE_WILDCARDS)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl, stretch=1)
        self.setLayout(sizer)

        self._ctrl.pathChanged.connect(self._on_path_changed)

    def SetFileTypes(self, file_types: str) -> None:
        """
        Execute the set file types operation.

        :param file_types: Value for ``file_types``.
        :type file_types: `str`
        """

        self._file_types = file_types

    def _on_path_changed(self, path: str) -> None:
        """
        Handle the path changed event.

        :param path: Filesystem path.
        :type path: `str`
        """

        if path == self._value:
            return

        self._value = path

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(str)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def GetValue(self) -> str:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: `str`
        """
        return self._value

    def SetValue(self, value: str) -> None:
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: `str`
        """

        self._value = value
        self._ctrl.SetValue(value)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
