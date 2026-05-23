# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base
from ..widgets import autocomplete_textctrl as _autocomplete_textctrl


class AutocompleteStringProperty(_prop_base.Property):
    """Represent an autocomplete string property in :mod:`harness_designer.ui.prop_ctrls.autocomplete_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label, style=0, units=None):
        """Initialise the :class:`AutocompleteStringProperty` instance.

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

        _prop_base.Property.__init__(self, parent, label)

        self._st = QLabel(label + ':', self)
        self._ctrl = _autocomplete_textctrl.AutoCompleteTextCtrl(self, choices=[])

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
            self._send_changed_event(str, self._value)
        else:
            self._value = text
