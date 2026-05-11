# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QRadioButton, QButtonGroup, QTabWidget
)
from PySide6.QtCore import Qt

from . import prop_base as _prop_base


class EnumProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label)
        self._choices = []
        self._value = 0
        self._labels = []
        self._button_group = None
        self._radio_box = None

    def _on_change(self, button_id):
        value = self._choices[button_id]
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(int, value)

    def SetValue(self, value: int):
        if value not in self._choices:
            return
        index = self._choices.index(value)
        self._value = value
        if self._button_group is not None:
            btn = self._button_group.button(index)
            if btn is not None:
                btn.blockSignals(True)
                btn.setChecked(True)
                btn.blockSignals(False)

    def GetValue(self) -> int:
        return self._value

    def Enable(self, flag=True):
        if self._radio_box is not None:
            self._radio_box.setEnabled(flag)

    def SetLabels(self, labels):
        self._labels = labels

        # Remove old radio box if present
        if self._radio_box is not None:
            self._sizer.removeWidget(self._radio_box)
            self._radio_box.deleteLater()
            self._radio_box = None

        box = QGroupBox(self.GetLabel(), self)
        grid = QHBoxLayout()
        grid.setContentsMargins(4, 4, 4, 4)

        bg = QButtonGroup(self)
        bg.setExclusive(True)

        for i, lbl in enumerate(labels):
            rb = QRadioButton(lbl, box)
            bg.addButton(rb, i)
            grid.addWidget(rb)

        box.setLayout(grid)
        bg.idClicked.connect(self._on_change)

        self._button_group = bg
        self._radio_box = box
        self._sizer.addWidget(box)

        # Re-apply current selection
        if self._value in self._choices:
            index = self._choices.index(self._value)
            btn = bg.button(index)
            if btn is not None:
                btn.setChecked(True)

        # Trigger parent relayout
        parent = self.parent()
        while parent is not None and not isinstance(parent, QTabWidget):
            parent = parent.parent()
        if parent is not None:
            parent.adjustSize()

    def GetLabels(self) -> list:
        return self._labels

    def GetItems(self) -> list:
        return self._choices

    def SetItems(self, items: list):
        self._choices = items
