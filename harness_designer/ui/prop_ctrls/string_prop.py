# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout

from PySide6 import QtCore
from PySide6 import QtWidgets
from . import events as _events


class StringProperty(QtWidgets.QWidget):
    """
    Represent a string property in
    :mod:`harness_designer.ui.prop_ctrls.string_prop`.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str, style: int = 0,
                 units: str | None = None, read_only: bool = False):
        """
        Initialise the :class:`StringProperty` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        :param style: Value for ``style``.
        :type style: `int`
        :param units: Value for ``units``.
        :type units: `str | None`
        :param read_only: Value for ``read_only``.
        :type read_only: `bool`
        """

        super().__init__(parent)

        self._value = ''
        self._label = label

        self._st = QLabel(label + ':', self)
        self._ctrl = QLineEdit(self)

        # Apply read-only state: either via explicit read_only=True or legacy
        # style=wx.TE_READONLY (integer 16) passed from unconverted call sites.
        if read_only or style == 16:
            self._ctrl.setReadOnly(True)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        sizer = QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(self._ctrl)
        sizer.addLayout(inner, stretch=1)

        if self._units_st:
            sizer.addWidget(
                self._units_st, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        self.setLayout(sizer)
        self._ctrl.returnPressed.connect(self._on_enter)

    def GetValue(self) -> str:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: `str`
        """

        return self._value

    def SetValue(self, value: str) -> None:
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: `str`
        """

        self._value = value
        self._ctrl.blockSignals(True)

        self._ctrl.setText(value)

        self._ctrl.blockSignals(False)

    def _on_enter(self) -> None:
        """
        Handle the enter event.
        """
        value = self._ctrl.text()
        if value == self._value:
            return

        self._value = value

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(str)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
