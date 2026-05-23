# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from . import prop_base as _prop_base


class StringProperty(_prop_base.Property):
    """Represent a string property in :mod:`harness_designer.ui.prop_ctrls.string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label, style=0, units=None, read_only=False):
        """Initialise the :class:`StringProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param style: Value for ``style``.
        :type style: UNKNOWN
        :param units: Value for ``units``.
        :type units: UNKNOWN
        :param read_only: Value for ``read_only``.
        :type read_only: UNKNOWN
        """
        _prop_base.Property.__init__(self, parent, label)
        self._value = ''

        self._st = QLabel(label + ':', self)
        self._ctrl = QLineEdit(self)

        # Apply read-only state: either via explicit read_only=True or legacy
        # style=wx.TE_READONLY (integer 16) passed from unconverted call sites.
        if read_only or style == 16:
            self._ctrl.setReadOnly(True)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(self._ctrl)
        row.addLayout(inner, stretch=1)

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

    def _on_enter(self):
        """Handle the enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        value = self._ctrl.text()
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(str, value)
