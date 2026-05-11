# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base
from ..widgets import autocomplete_combobox as _autocomplete_combobox


class ComboBoxProperty(_prop_base.Property):

    def __init__(self, parent, label, units=None):
        _prop_base.Property.__init__(self, parent, label)
        self._choices = []
        self._value = ''

        self._st = QLabel(label + ':', self)
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(self)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self._ctrl)
        row.addLayout(col, stretch=1)

        if self._units_st:
            row.addWidget(self._units_st, alignment=Qt.AlignBottom)

        self._sizer.addLayout(row)

        self._ctrl.currentTextChanged.connect(self._on_change)
        self._ctrl.lineEdit().returnPressed.connect(self._on_change_from_enter)

    def _on_change(self, value):
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(str, value)

    def _on_change_from_enter(self):
        self._on_change(self._ctrl.currentText())

    def SetValue(self, value: str):
        self._value = value
        self._ctrl.blockSignals(True)
        if value in self._choices:
            self._ctrl.setCurrentText(value)
        else:
            self._ctrl.lineEdit().setText(value)
        self._ctrl.blockSignals(False)

    def GetValue(self) -> str:
        return self._value

    def Clear(self):  # NOQA
        self._choices = []
        self._ctrl.clear()

    def GetItems(self) -> list:
        return self._choices

    def SetItems(self, items: list):
        self._choices = items
        self._ctrl.blockSignals(True)
        self._ctrl.clear()
        self._ctrl.addItems(items)
        self._ctrl.blockSignals(False)
