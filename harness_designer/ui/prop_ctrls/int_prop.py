# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import events as _events


class IntProperty(QtWidgets.QWidget):
    """Represent an int property in :mod:`harness_designer.ui.prop_ctrls.int_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str, min_value: int, max_value: int, units: str | None = None):
        """Initialise the :class:`IntProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        :param min_value: Value for ``min_value``.
        :type min_value: `int`
        :param max_value: Value for ``max_value``.
        :type max_value: `int`
        :param units: Value for ``units``.
        :type units: `str | None`
        """

        super().__init__(parent)

        self._min_val = min_value
        self._max_val = max_value
        self._value = min_value
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = QtWidgets.QSpinBox(self)
        self._ctrl.setRange(min_value, max_value)
        self._ctrl.setValue(min_value)

        self._units_st = None
        if units is not None:
            self._units_st = QtWidgets.QLabel(units, self)

        self._slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._slider.setRange(min_value, max_value)
        self._slider.setValue(min_value)

        left_col = QtWidgets.QVBoxLayout()
        left_col.setContentsMargins(0, 5, 0, 0)
        left_col.addWidget(self._st)

        spin_row = QtWidgets.QHBoxLayout()
        spin_row.addWidget(self._ctrl, stretch=1)

        if self._units_st:
            spin_row.addWidget(self._units_st)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.addLayout(spin_row)
        right_col.addWidget(self._slider)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addLayout(left_col)
        sizer.addLayout(right_col, stretch=1)

        self.setLayout(sizer)

        self._slider.valueChanged.connect(self._on_slider_scroll)
        self._ctrl.valueChanged.connect(self._on_spin_changed)

    def SetValue(self, value: int) -> None:
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: `int`
        """

        value = max(self._min_val, min(self._max_val, value))
        self._value = value

        self._ctrl.blockSignals(True)
        self._slider.blockSignals(True)

        self._ctrl.setValue(value)
        self._slider.setValue(value)

        self._ctrl.blockSignals(False)
        self._slider.blockSignals(False)

    def GetValue(self) -> int:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: `int`
        """
        return self._value

    def _on_slider_scroll(self, value: int) -> None:
        """
        Handle the slider scroll event.

        :param value: Value to store or process.
        :type value: `int`
        """

        self._value = value
        self._ctrl.blockSignals(True)

        self._ctrl.setValue(value)

        self._ctrl.blockSignals(False)

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(int)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def _on_spin_changed(self, value: int) -> None:
        """
        Handle the spin changed event.

        :param value: Value to store or process.
        :type value: `int`
        """

        self._value = value
        self._slider.blockSignals(True)

        self._slider.setValue(value)

        self._slider.blockSignals(False)

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(int)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
