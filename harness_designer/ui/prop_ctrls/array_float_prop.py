# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLineEdit, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QDialog

from . import prop_base as _prop_base
from ._array_dialog_base import _ArrayDialog


def _float_char_ok(key: int) -> bool:
    # digits 0-9, minus, decimal point, or non-printable
    return key < 32 or (48 <= key <= 57) or key in (45, 46)


class ArrayFloatDialog(_ArrayDialog):
    _char_filter = staticmethod(_float_char_ok)

    def __init__(self, parent, values, title='Modify Array'):
        _ArrayDialog.__init__(self, parent, values, title)

    def GetValue(self) -> list:
        result = []
        for v in self._raw_values():
            try:
                result.append(float(v))
            except ValueError:
                pass
        return result


class ArrayFloatProperty(_prop_base.Property):

    def __init__(self, parent, label):
        self._dialog_title = 'Enter Decimal Values'
        _prop_base.Property.__init__(self, parent, label)
        self._value = []

        self._st = QLabel(label + ':', self)
        self._ctrl = QLineEdit(self)
        self._ctrl.setReadOnly(True)
        self._button = QPushButton('...', self)
        self._button.setFixedWidth(20)

        inner = QHBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(self._ctrl, stretch=1)
        inner.addWidget(self._button)

        col = QVBoxLayout()
        col.setContentsMargins(0, 5, 0, 5)
        col.addLayout(inner)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)
        row.addLayout(col, stretch=1)
        self._sizer.addLayout(row)

        self._button.clicked.connect(self._on_dialog_button)

    def GetValue(self) -> list:
        return self._value

    def SetValue(self, value: list):
        self._value = value
        self._ctrl.setText(', '.join(str(v) for v in value))

    def SetDialogTitle(self, value: str):
        self._dialog_title = value

    def _on_dialog_button(self):
        dlg = ArrayFloatDialog(self, self._value, self._dialog_title)
        dlg.adjustSize()
        dlg.move(self.mapToGlobal(self.rect().center()) - dlg.rect().center())
        if dlg.exec() == QDialog.Accepted:
            value = dlg.GetValue()
            if value == self._value:
                return
            self._value = value
            self._ctrl.setText(', '.join(str(v) for v in value))
            self._send_changed_event(list, self._value)
