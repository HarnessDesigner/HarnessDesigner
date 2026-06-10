# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from PySide6 import QtWidgets
from PySide6 import QtCore

from ._path_ctrl_base import PathCtrl
from . import events as _events


class PathProperty(QtWidgets.QWidget):
    """Represent a path property in :mod:`harness_designer.ui.prop_ctrls.path_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str):
        """Initialise the :class:`PathProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        """

        super().__init__(parent)

        self._value = ''
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = PathCtrl(self, '', wildcard='', http_browse=False)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl, stretch=1)
        self.setLayout(sizer)

        # on_path_char equivalent: enable/disable browse button based on 'http' prefix
        self._ctrl.path_ctrl.textEdited.connect(self._on_text_edited)
        self._ctrl.pathChanged.connect(self._on_path_changed)

    def _on_text_edited(self, _) -> None:
        """
        Handle the text edited event.
        """

        QtCore.QTimer.singleShot(0, lambda: self._ctrl.path_button.setEnabled(
            not self._ctrl.path_ctrl.text().startswith('http')))

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

    def SetWildcards(self, value: str) -> None:
        """
        Execute the set wildcards operation.

        :param value: Value to store or process.
        :type value: `str`
        """

        self._ctrl.SetWildcards(value)

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
        self._ctrl.path_button.setEnabled(not value.startswith('http'))

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
