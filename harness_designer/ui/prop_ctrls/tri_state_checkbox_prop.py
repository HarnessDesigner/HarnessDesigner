# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from ..widgets import tri_state_checkbox_ctrl as _tri_state_checkbox_ctrl
from . import events as _events


class TriStateCheckboxProperty(QtWidgets.QWidget):
    """
    Represent a 3 state checkbox property in
    :mod:`harness_designer.ui.prop_ctrls.tri_state_checkbox_prop`.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label):
        """Initialise the :class:`BoolProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """

        super().__init__(parent)

        self._value = False
        self._label = label

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)

        self._ctrl = _tri_state_checkbox_ctrl.TriStateCheckboxCtrl(self, label + ':')
        sizer.addWidget(self._ctrl)
        sizer.addStretch(1)
        self.setLayout(sizer)

        self._ctrl.checkStateChanged.connect(self._on_change)

    def _on_change(self, value: bool | None):
        """
        Handle the change event.

        :type value: `bool | None`
        """

        if value == self._value:
            return

        self._value = value

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(object)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetValue(self, value: bool | None):
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: `bool | None`
        """
        self._value = value
        self._ctrl.SetValue(value)

    def GetValue(self) -> bool | None:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: `bool | None`
        """

        return self._ctrl.GetValue()

    def SetLabel(self, value: str):
        self._label = value
        self._ctrl.SetLabel(value)

    def GetLabel(self) -> str:
        return self._label
