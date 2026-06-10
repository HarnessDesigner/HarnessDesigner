# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from ..widgets import autocomplete_combobox as _autocomplete_combobox
from . import events as _events


class ComboBoxProperty(QtWidgets.QWidget):
    """
    Represent a combo box property in
    :mod:`harness_designer.ui.prop_ctrls.combobox_prop`.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str, units: str | None = None):
        """
        Initialise the :class:`ComboBoxProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        :param units: Value for ``units``.
        :type units: `str | None`
        """
        super().__init__(parent)

        self._choices = []
        self._value = ''
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = _autocomplete_combobox.AutoCompleteComboBox(self)

        self._units_st = None
        if units is not None:
            self._units_st = QtWidgets.QLabel(units, self)

        sizer = QtWidgets.QHBoxLayout(self)
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl)

        if self._units_st:
            sizer.addWidget(
                self._units_st, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        self.setLayout(sizer)

        self._ctrl.currentTextChanged.connect(self._on_change)
        self._ctrl.lineEdit().returnPressed.connect(self._on_change_from_enter)

    def _on_change(self, value: str) -> None:
        """
        Handle the change event.

        :param value: Value to store or process.
        :type value: `str`
        """

        if value == self._value:
            return

        self._value = value

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(str)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def _on_change_from_enter(self) -> None:
        """
        Handle the change from enter event.
        """

        self._on_change(self._ctrl.currentText())

    def SetValue(self, value: str) -> None:
        """
        Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """

        self._value = value
        self._ctrl.blockSignals(True)

        if value in self._choices:
            self._ctrl.setCurrentText(value)
        else:
            self._ctrl.lineEdit().setText(value)

        self._ctrl.blockSignals(False)

    def GetValue(self) -> str:
        """
        Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """

        return self._value

    def Clear(self) -> None:
        """
        Execute the clear operation.
        """

        self._choices = []
        self._ctrl.clear()

    def GetItems(self) -> list[str]:
        """
        Execute the get items operation.

        :returns: Return value. UNKNOWN details.
        :rtype: `list[str]`
        """

        return self._choices

    def SetItems(self, items: list[str]):
        """
        Execute the set items operation.

        :param items: Collection of items to process.
        :type items: list[str]
        """

        self._choices = items
        self._ctrl.blockSignals(True)

        self._ctrl.clear()
        self._ctrl.addItems(items)

        self._ctrl.blockSignals(False)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
