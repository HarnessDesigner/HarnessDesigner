# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from PySide6 import QtWidgets
from PySide6 import QtCore

from ._path_ctrl_base import PathCtrl
from ._image_ctrl_base import ImageCtrl
from ... import utils as _utils
from . import events as _events


class ImageProperty(QtWidgets.QWidget):
    """
    Represent an image property in
    :mod:`harness_designer.ui.prop_ctrls.image_prop`.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str):
        """
        Initialise the :class:`ImageProperty` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        """
        super().__init__(parent)

        self._value = ''
        self._file_types = {}
        self._save_path = None
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)

        self._ctrl = PathCtrl(
            self, '', wildcard=_utils.IMAGE_FILE_WILDCARDS)

        self._image = ImageCtrl(
            self, {}, '', None, support_pdf=False)

        sizer = QtWidgets.QVBoxLayout()
        top_row = QtWidgets.QHBoxLayout()
        top_row.setContentsMargins(5, 2, 5, 2)
        top_row.addWidget(self._st)
        top_row.addWidget(self._ctrl, stretch=1)
        sizer.addLayout(top_row)

        img_row = QtWidgets.QHBoxLayout()
        img_row.setContentsMargins(5, 2, 5, 2)
        img_row.addWidget(self._image, stretch=1)
        sizer.addLayout(img_row)

        self.setLayout(sizer)

        self._ctrl.pathChanged.connect(self._on_path_changed)

    def SetFileTypes(self, file_types: str) -> None:
        """
        Execute the set file types operation.

        :param file_types: Value for ``file_types``.
        :type file_types: `str``
        """

        self._file_types = file_types
        self._image.SetFileTypes(file_types)

    def _on_path_changed(self, path: str) -> None:
        """
        Handle the path changed event.

        :param path: Filesystem path.
        :type path: `str`
        """

        if path == self._value:
            return
        if self._image.SetValue(path):
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
        :rtype: str
        """

        return self._value

    def SetValue(self, value: str) -> None:
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: `str``
        """

        self._value = value[0]
        self._save_path = value[1]

        if value[1] is None:
            self._image.SetValue(value[0])
        else:
            self._image.SetValue(value[1])

        self._ctrl.SetValue(value[0])

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
