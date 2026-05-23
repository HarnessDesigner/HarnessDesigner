# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base
from ..widgets import autocomplete_combobox as _autocomplete_combobox


class ComboBoxProperty(_prop_base.Property):
    """Represent a combo box property in :mod:`harness_designer.ui.prop_ctrls.combobox_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label, units=None):
        """Initialise the :class:`ComboBoxProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param units: Value for ``units``.
        :type units: UNKNOWN
        """
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
        """Handle the change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(str, value)

    def _on_change_from_enter(self):
        """Handle the change from enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._on_change(self._ctrl.currentText())

    def SetValue(self, value: str):
        """Execute the set value operation.

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
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._value

    def Clear(self):  # NOQA
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._choices = []
        self._ctrl.clear()

    def GetItems(self) -> list:
        """Execute the get items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list
        """
        return self._choices

    def SetItems(self, items: list):
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: list
        """
        self._choices = items
        self._ctrl.blockSignals(True)
        self._ctrl.clear()
        self._ctrl.addItems(items)
        self._ctrl.blockSignals(False)
