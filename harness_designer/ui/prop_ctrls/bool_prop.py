# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import events as _events


class BoolProperty(QtWidgets.QWidget):
    """Represent a bool property in :mod:`harness_designer.ui.prop_ctrls.bool_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
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

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = QtWidgets.QCheckBox('', self)

        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl)
        sizer.addStretch(1)
        self.setLayout(sizer)

        self._ctrl.checkStateChanged.connect(self._on_change)

    def _on_change(self, _):
        """Handle the change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        value = self._ctrl.isChecked()
        if value == self._value:
            return

        self._value = value

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(bool)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetValue(self, value: bool):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._value = value
        self._ctrl.blockSignals(True)

        self._ctrl.setChecked(value)

        self._ctrl.blockSignals(False)

    def GetValue(self) -> bool:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._ctrl.isChecked()

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
