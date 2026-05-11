# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QColorDialog
from PySide6.QtGui import QColor

from . import prop_base as _prop_base
from ..widgets import autocomplete_combobox as _autocomplete_combobox


class ColorProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label)
        self._value = ['None', QColor(0, 0, 0)]
        self._choices = []

        self._st = QLabel(label + ':', self)
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(self)
        self._ctrl.lineEdit().setText('None')

        self._button = QPushButton(self)
        self._button.setFixedSize(24, 24)
        self._button.setStyleSheet('background-color: black;')

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)

        inner = QHBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(self._ctrl, stretch=1)
        inner.addWidget(self._button)
        col.addLayout(inner)

        row.addLayout(col, stretch=1)
        self._sizer.addLayout(row)

        self._ctrl.currentTextChanged.connect(self._on_change)
        self._ctrl.lineEdit().returnPressed.connect(
            lambda: self._on_change(self._ctrl.currentText()))
        self._button.clicked.connect(self._on_colour)

    def _on_colour(self):
        current = self._value[1] if isinstance(self._value[1], QColor) else QColor(0, 0, 0)
        color = QColorDialog.getColor(current, self, 'Select Colour')
        if not color.isValid():
            return

        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
        rgba = r << 24 | g << 16 | b << 8 | a

        self._button.setStyleSheet(f'background-color: {color.name()};')

        colors = [item[1] for item in self._choices]
        if rgba in colors:
            index = colors.index(rgba)
            name = self._choices[index][0]
            self._ctrl.blockSignals(True)
            self._ctrl.setCurrentText(name)
            self._ctrl.blockSignals(False)
            self._value = [name, color]
        else:
            name = self._ctrl.currentText()
            self._value = [name, color]

        self._send_changed_event(list, self._value)

    def _on_change(self, value):
        values = [item[0] for item in self._choices]
        if value in values:
            index = values.index(value)
            rgba = self._choices[index][1]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            color = QColor(r, g, b, a)
            self._button.setStyleSheet(f'background-color: {color.name()};')
            self._value = [value, color]
        else:
            self._button.setStyleSheet('background-color: black;')
            self._value = [value, QColor(0, 0, 0)]

        self._send_changed_event(list, self._value)

    def SetValue(self, value):
        values = [item[0] for item in self._choices]
        self._ctrl.blockSignals(True)
        if value[0] in values:
            self._ctrl.setCurrentText(value[0])
        else:
            self._ctrl.lineEdit().setText(value[0])

        color = value[1]
        if isinstance(color, QColor):
            self._button.setStyleSheet(f'background-color: {color.name()};')
        self._ctrl.blockSignals(False)
        self._value = list(value)

    def GetValue(self):
        return self._value

    def Clear(self):  # NOQA
        self._choices = []
        self._ctrl.clear()

    def GetItems(self):
        return self._choices

    def SetItems(self, items):
        self._choices = items
        self._ctrl.blockSignals(True)
        self._ctrl.clear()
        self._ctrl.addItems([item[0] for item in items])
        self._ctrl.blockSignals(False)
