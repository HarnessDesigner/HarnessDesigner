# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from PySide6 import QtGui
from PySide6 import QtWidgets
from PySide6 import QtCore

from ..widgets import autocomplete_combobox as _autocomplete_combobox
from . import events as _events
from ... import color as _color


class ColorProperty(QtWidgets.QWidget):
    """Represent a color property in :mod:`harness_designer.ui.prop_ctrls.color_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label):
        """Initialise the :class:`ColorProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """

        super().__init__(parent)

        self._value = ['None', QtGui.QColor(0, 0, 0)]
        self._choices = []
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(self)
        self._ctrl.lineEdit().setText('None')

        self._button = QtWidgets.QPushButton(self)
        self._button.setFixedSize(24, 24)
        self._button.setStyleSheet('background-color: black;')

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl, stretch=1)
        sizer.addWidget(self._button)
        self.setLayout(sizer)

        self._ctrl.currentTextChanged.connect(self._on_change)

        self._ctrl.lineEdit().returnPressed.connect(
            lambda: self._on_change(self._ctrl.currentText()))

        self._button.clicked.connect(self._on_colour)

    def _on_colour(self):
        """Handle the colour event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        current = self._value[1] if isinstance(self._value[1], QtGui.QColor) else QtGui.QColor(0, 0, 0)
        color = QtWidgets.QColorDialog.getColor(current, self, 'Select Colour')
        if not color.isValid():
            return

        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
        rgba = r << 24 | g << 16 | b << 8 | a

        self._button.setStyleSheet(f'background-color: {color.name()};')

        color = _color.Color(r, g, b, a)

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

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(list)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def _on_change(self, value):
        """Handle the change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        values = [item[0] for item in self._choices]
        if value in values:
            index = values.index(value)
            rgba = self._choices[index][1]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            color = QtGui.QColor(r, g, b, a)
            self._button.setStyleSheet(f'background-color: {color.name()};')
            color = _color.Color(r, g, b, a)
            self._value = [value, color]
        else:
            self._button.setStyleSheet('background-color: black;')

            color = _color.Color(0, 0, 0, 255)
            self._value = [value, color]

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(list)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetValue(self, value: list[str, _color.Color | QtGui.QColor] | tuple[str, _color.Color | QtGui.QColor]):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        values = [item[0] for item in self._choices]
        self._ctrl.blockSignals(True)

        name, color = value

        if isinstance(color, _color.Color):
            qcolor = color.to_qcolor()
        elif isinstance(color, QtGui.QColor):
            qcolor = color
            color = _color.Color(color.red(), color.green(), color.blue(), 255)
        else:
            if name not in values:
                name = 'Black'

            index = values.index(name)
            rgba = self._choices[index][1]
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            a = rgba & 0xFF
            qcolor = QtGui.QColor(r, g, b, a)
            color = _color.Color(r, g, b, a)

        if name in values:
            self._ctrl.setCurrentText(name)
        else:
            self._ctrl.lineEdit().setText(name)

        self._button.setStyleSheet(f'background-color: {qcolor.name()};')

        self._ctrl.blockSignals(False)
        self._value = [name, color]

    def GetValue(self) -> list[str, _color.Color]:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list[str, _color.Color]
        """
        return self._value

    def Clear(self):  # NOQA
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._choices = []
        self._ctrl.clear()

    def GetItems(self):
        """Execute the get items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._choices

    def SetItems(self, items):
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self._choices = items
        self._ctrl.blockSignals(True)

        self._ctrl.clear()
        self._ctrl.addItems([item[0] for item in items])

        self._ctrl.blockSignals(False)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
