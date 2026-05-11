# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QSpinBox, QSlider, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base


class IntProperty(_prop_base.Property):

    def __init__(self, parent, label, min_value: int, max_value: int, units=None):
        _prop_base.Property.__init__(self, parent, label)

        self._min_val = min_value
        self._max_val = max_value
        self._value = min_value

        self._st = QLabel(label + ':', self)
        self._ctrl = QSpinBox(self)
        self._ctrl.setRange(min_value, max_value)
        self._ctrl.setValue(min_value)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        self._slider = QSlider(Qt.Horizontal, self)
        self._slider.setRange(min_value, max_value)
        self._slider.setValue(min_value)

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

    def SetValue(self, value: int):
        value = max(self._min_val, min(self._max_val, value))
        self._value = value
        self._ctrl.blockSignals(True)
        self._slider.blockSignals(True)
        self._ctrl.setValue(value)
        self._slider.setValue(value)
        self._ctrl.blockSignals(False)
        self._slider.blockSignals(False)

    def GetValue(self) -> int:
        return self._value

    def _on_slider_scroll(self, value):
        self._value = value
        self._ctrl.blockSignals(True)
        self._ctrl.setValue(value)
        self._ctrl.blockSignals(False)
        self._send_changed_event(int, value)

    def _on_spin_changed(self, value):
        self._value = value
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider.blockSignals(False)
        self._send_changed_event(int, value)
