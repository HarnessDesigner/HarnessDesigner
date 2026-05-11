# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base


class StringProperty(_prop_base.Property):

    def __init__(self, parent, label, style=0, units=None):
        _prop_base.Property.__init__(self, parent, label)
        self._value = ''

        self._st = QLabel(label + ':', self)
        self._ctrl = QLineEdit(self)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(self._ctrl)
        row.addLayout(inner, stretch=1)

        if self._units_st:
            row.addWidget(self._units_st, alignment=Qt.AlignBottom)

        self._sizer.addLayout(row)
        self._ctrl.returnPressed.connect(self._on_enter)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._value = value
        self._ctrl.blockSignals(True)
        self._ctrl.setText(value)
        self._ctrl.blockSignals(False)

    def _on_enter(self):
        value = self._ctrl.text()
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(str, value)
