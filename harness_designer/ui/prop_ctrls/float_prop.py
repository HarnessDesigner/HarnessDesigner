# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QDoubleSpinBox, QSlider, QLabel, QHBoxLayout, QVBoxLayout
)
from PySide6.QtCore import Qt

from . import prop_base as _prop_base
from ... import utils as _utils
from ...geometry.decimal import Decimal as _d


class FloatProperty(_prop_base.Property):

    def __init__(self, parent, label, min_value: float, max_value: float,
                 increment: float, units=None):
        _prop_base.Property.__init__(self, parent, label)

        self._min_val = min_value
        self._max_val = max_value
        self._value = min_value
        self._inc = increment

        precision = 0
        inc = _d(increment)
        while inc < 1:
            precision += 1
            inc *= _d(10.0)
        self._precision = precision

        s_inc = _d(10) * _d(precision)
        slider_max = _d(100) * s_inc
        self._s_max = max(1, int(slider_max))

        self._st = QLabel(label + ':', self)
        self._ctrl = QDoubleSpinBox(self)
        self._ctrl.setRange(min_value, max_value)
        self._ctrl.setSingleStep(increment)
        self._ctrl.setDecimals(precision)
        self._ctrl.setValue(min_value)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        slider_value = _utils.remap(min_value, min_value, max_value, 0, self._s_max)
        self._slider = QSlider(Qt.Horizontal, self)
        self._slider.setRange(0, self._s_max)
        self._slider.setValue(int(slider_value))

        # layout
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 5, 0, 0)
        left_col.addWidget(self._st)

        spin_row = QHBoxLayout()
        spin_row.addWidget(self._ctrl, stretch=1)
        if self._units_st:
            spin_row.addWidget(self._units_st)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.addLayout(spin_row)
        right_col.addWidget(self._slider)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addLayout(left_col)
        row.addLayout(right_col, stretch=1)
        self._sizer.addLayout(row)

        self._slider.valueChanged.connect(self._on_slider_scroll)
        self._ctrl.valueChanged.connect(self._on_spin_changed)

    def SetValue(self, value: float):
        value = round(value, self._precision)
        value = _d(value)
        inc = _d(self._inc)
        remaining = value % inc
        if remaining:
            value += inc - remaining
        if value > self._max_val:
            value = self._max_val
        if value < self._min_val:
            value = self._min_val
        self._value = float(value)

        self._ctrl.blockSignals(True)
        self._slider.blockSignals(True)
        self._ctrl.setValue(self._value)
        sv = _utils.remap(value, self._min_val, self._max_val, 0, self._s_max)
        self._slider.setValue(int(sv))
        self._ctrl.blockSignals(False)
        self._slider.blockSignals(False)

    def GetValue(self) -> float:
        return self._value

    def _on_slider_scroll(self, _):
        sv = self._slider.value()
        spin_value = _utils.remap(sv, 0, self._s_max, self._min_val, self._max_val)
        inc = _d(self._inc)
        remaining = spin_value % inc
        if remaining:
            spin_value += inc - remaining
        self._value = float(spin_value)

        self._ctrl.blockSignals(True)
        self._ctrl.setValue(self._value)
        self._ctrl.blockSignals(False)
        self._send_changed_event(float, self._value)

    def _on_spin_changed(self, spin_value):
        sv = _utils.remap(spin_value, self._min_val, self._max_val, 0, self._s_max)
        self._value = spin_value

        self._slider.blockSignals(True)
        self._slider.setValue(int(sv))
        self._slider.blockSignals(False)
        self._send_changed_event(float, spin_value)
