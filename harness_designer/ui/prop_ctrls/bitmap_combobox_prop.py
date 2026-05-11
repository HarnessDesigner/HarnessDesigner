# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base
from ..widgets import bitmap_autocomplete_combobox as _bitmap_autocomplete_combobox


class BitmapComboBoxProperty(_prop_base.Property):

    def __init__(self, parent, label):
        self._choices = []
        self._value = ''
        self._units = None
        self._units_st = None
        self._tooltip = None

        _prop_base.Property.__init__(self, parent, label)

        self._st = QLabel(label + ':', self)
        self._ctrl = _bitmap_autocomplete_combobox.BitmapAutoCompleteComboBox(self)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)
        row.addWidget(self._ctrl, stretch=1)

        if self._units_st:
            row.addWidget(self._units_st)

        self._sizer.addLayout(row)

        self._ctrl.currentTextChanged.connect(self._on_change)
        self._ctrl.lineEdit().returnPressed.connect(
            lambda: self._on_change(self._ctrl.currentText()))

        if self._tooltip is not None:
            self._ctrl.setToolTip(self._tooltip)
            self._st.setToolTip(self._tooltip)

    def _on_change(self, value=None):
        if value is None:
            value = self._ctrl.currentText()
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(str, value)

    def SetValue(self, value: str):
        self._value = value
        self._ctrl.blockSignals(True)
        items = [self._ctrl.itemText(i) for i in range(self._ctrl.count())]
        if value in items:
            self._ctrl.setCurrentText(value)
        else:
            self._ctrl.lineEdit().setText(value)
        self._ctrl.blockSignals(False)

    def GetValue(self) -> str:
        return self._ctrl.currentText()

    def Clear(self):  # NOQA
        self._ctrl.clear()

    def GetItems(self) -> list:
        return [self._ctrl.itemText(i) for i in range(self._ctrl.count())]

    def SetItems(self, items: list):
        self._ctrl.blockSignals(True)
        self._ctrl.clear()
        self._ctrl.addItems(items)
        self._ctrl.blockSignals(False)
