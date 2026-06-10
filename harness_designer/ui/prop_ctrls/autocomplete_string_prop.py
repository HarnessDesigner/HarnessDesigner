# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from ..widgets import autocomplete_textctrl as _autocomplete_textctrl
from . import events as _events


class AutocompleteStringProperty(QtWidgets.QWidget):
    """Represent an autocomplete string property in :mod:`harness_designer.ui.prop_ctrls.autocomplete_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label, style=0, units=None):
        """
        Initialise the :class:`AutocompleteStringProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param style: Value for ``style``.
        :type style: UNKNOWN
        :param units: Value for ``units``.
        :type units: UNKNOWN
        """
        self._choices = []
        self._value = ''
        self._units_st = None
        self._label = label

        super().__init__(parent)

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = _autocomplete_textctrl.AutoCompleteTextCtrl(self, choices=[])

        if units is not None:
            self._units_st = QtWidgets.QLabel(units, self)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)

        col = QtWidgets.QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self._ctrl)
        sizer.addLayout(col, stretch=1)

        if self._units_st:
            sizer.addWidget(
                self._units_st, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        self.setLayout(sizer)
        self._ctrl.returnPressed.connect(self._on_enter)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._value

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._value = value
        self._ctrl.blockSignals(True)

        self._ctrl.setText(value)

        self._ctrl.blockSignals(False)

    def SetItems(self, items: list) -> None:
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: list
        """
        self._choices = items
        if self._ctrl is not None:
            self._ctrl.SetItems(items)

    def _on_enter(self):
        """Handle the enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        # Reproduce the original double-enter-to-commit multiline logic.
        text = self._ctrl.text()
        if text.endswith('\n\n') and self._value.endswith('\n'):
            self._value = text.rstrip()
            self._choices.append(self._value)
            self._ctrl.SetItems(self._choices)
            self._ctrl.blockSignals(True)
            self._ctrl.setText(self._value)
            self._ctrl.blockSignals(False)

            evt = _events.PropertyEvent()
            evt.SetValue(self._value)
            evt.SetPropertyType(str)
            evt.SetProperty(self)
            self.propertyChanged.emit(evt)
        else:
            self._value = text

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
