from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from .combobox_ctrl import ComboBoxCtrl
from ... import color as _color


class ColorCtrl(QtWidgets.QWidget):
    """
    Label + combobox + colour-picker-button composite widget.

    Emits colour_changed(Color) whenever the selection or the picker changes.
    Call sites should connect to this signal instead of binding
    EVT_COLOURPICKER_CHANGED on the old sizer-based widget.
    """

    colour_changed: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent=None, label: str = '', table=None):
        """Initialise the :class:`ColorCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        :param table: Value for ``table``.
        :type table: UNKNOWN
        """
        super().__init__(parent)

        table.execute('SELECT id, name, rgb FROM colors;')
        rows = table.fetchall()
        self._choices = sorted(rows, key=lambda x: x[1])

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.ctrl = ComboBoxCtrl(
            self, label, [item[1] for item in self._choices])

        self.button = QtWidgets.QPushButton(self)
        self.button.setFixedWidth(32)
        self._current_qcolor = QtGui.QColor(255, 255, 255, 255)
        self._update_button_colour(self._current_qcolor)

        layout.addWidget(self.ctrl, 2)
        layout.addWidget(self.button, 0)

        self.ctrl.currentTextChanged.connect(self._on_combobox)
        self.button.clicked.connect(self._on_colour_button)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _update_button_colour(self, qc: QtGui.QColor):
        """Update the button colour.

        UNKNOWN details are inferred from the callable name and signature.

        :param qc: Value for ``qc``.
        :type qc: :class:`QtGui.QColor`
        """
        self._current_qcolor = qc
        r, g, b = qc.red(), qc.green(), qc.blue()
        self.button.setStyleSheet(f'QPushButton {{ '
                                  f'background-color: rgb({r},{g},{b});'
                                  f' border: 1px solid #666; }}')

    @staticmethod
    def _rgba_from_qcolor(_: str, qc: QtGui.QColor) -> int:
        """Execute the RGBA from qcolor operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: str
        :param qc: Value for ``qc``.
        :type qc: :class:`QtGui.QColor`
        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        r, g, b = qc.red(), qc.green(), qc.blue()

        return r << 24 | g << 16 | b << 8 | 0xFF

    def _on_colour_button(self):
        """Handle the colour button event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        qc = QtWidgets.QColorDialog.getColor(
            self._current_qcolor, self, 'Select Colour')

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
        """Handle the combobox event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        values = [item[1] for item in self._choices]
        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            qc = QtGui.QColor(r, g, b, a)
            self._update_button_colour(qc)

        self.colour_changed.emit(self.GetColour())

    # ------------------------------------------------------------------
    # wx-compatible public API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        """Execute the enable operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self.ctrl.setEnabled(flag)
        self.button.setEnabled(flag)

    def SetToolTip(self, text: str):
        """Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self.ctrl.setToolTip(text)
        self.button.setToolTip(text)

    SetToolTipString = SetToolTip

    def GetColour(self) -> '_color.Color':
        """Execute the get colour operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_color.Color`
        """
        qc = self._current_qcolor
        name = self.GetValue()

        if name in ('None', 'Transparent'):
            a = 0
        else:
            a = 255

        return _color.Color(qc.red(), qc.green(), qc.blue(), a)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.ctrl.GetValue()

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        values = [item[1] for item in self._choices]
        if value in values:
            index = values.index(value)
            rgba = self._choices[index][2]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            self._update_button_colour(QtGui.QColor(r, g, b, a))

        self.ctrl.SetValue(value)
