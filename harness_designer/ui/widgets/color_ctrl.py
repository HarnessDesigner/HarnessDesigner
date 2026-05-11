from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QColorDialog
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal

from .combobox_ctrl import ComboBoxCtrl
from ... import color as _color


class ColorCtrl(QWidget):
    """Label + combobox + colour-picker-button composite widget.

    Emits colour_changed(Color) whenever the selection or the picker changes.
    Call sites should connect to this signal instead of binding
    EVT_COLOURPICKER_CHANGED on the old sizer-based widget.
    """

    colour_changed = Signal(object)  # emits a _color.Color

    def __init__(self, parent=None, label: str = '', table=None):
        super().__init__(parent)

        table.execute('SELECT id, name, rgb FROM colors;')
        rows = table.fetchall()
        self._choices = sorted(rows, key=lambda x: x[1])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.ctrl = ComboBoxCtrl(self, label, [item[1] for item in self._choices])
        self.button = QPushButton(self)
        self.button.setFixedWidth(32)
        self._current_qcolor = QColor(255, 255, 255, 255)
        self._update_button_colour(self._current_qcolor)

        layout.addWidget(self.ctrl, 2)
        layout.addWidget(self.button, 0)

        self.ctrl.currentTextChanged.connect(self._on_combobox)
        self.button.clicked.connect(self._on_colour_button)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _update_button_colour(self, qc: QColor):
        self._current_qcolor = qc
        r, g, b = qc.red(), qc.green(), qc.blue()
        self.button.setStyleSheet(
            f'QPushButton {{ background-color: rgb({r},{g},{b}); border: 1px solid #666; }}'
        )

    def _rgba_from_qcolor(self, name: str, qc: QColor) -> int:
        r, g, b = qc.red(), qc.green(), qc.blue()
        return r << 24 | g << 16 | b << 8 | 0xFF

    def _on_colour_button(self):
        qc = QColorDialog.getColor(self._current_qcolor, self, 'Select Colour')
        if not qc.isValid():
            return
        self._update_button_colour(qc)

        # Try to match a named colour and update the combobox
        rgba = self._rgba_from_qcolor('', qc)
        colors = [item[2] for item in self._choices]
        if rgba in colors:
            index = colors.index(rgba)
            name = self._choices[index][1]
            self.ctrl.blockSignals(True)
            self.ctrl.SetValue(name)
            self.ctrl.blockSignals(False)

        self.colour_changed.emit(self.GetColour())

    def _on_combobox(self, value: str):
        values = [item[1] for item in self._choices]
        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            qc = QColor(r, g, b, a)
            self._update_button_colour(qc)

        self.colour_changed.emit(self.GetColour())

    # ------------------------------------------------------------------
    # wx-compatible public API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        self.ctrl.setEnabled(flag)
        self.button.setEnabled(flag)

    def SetToolTip(self, text: str):
        self.ctrl.setToolTip(text)
        self.button.setToolTip(text)

    SetToolTipString = SetToolTip

    def GetColour(self) -> '_color.Color':
        qc = self._current_qcolor
        name = self.GetValue()
        a = 0 if name in ('None', 'Transparent') else 255
        return _color.Color(qc.red(), qc.green(), qc.blue(), a)

    def GetValue(self) -> str:
        return self.ctrl.GetValue()

    def SetValue(self, value: str):
        values = [item[1] for item in self._choices]
        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            self._update_button_colour(QColor(r, g, b, a))
        self.ctrl.SetValue(value)
