# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from PySide6 import QtWidgets
from PySide6 import QtCore

from ._array_dialog_base import _ArrayDialog
from . import events as _events


class ArrayStringDialog(_ArrayDialog):
    """Represent an array string dialog in :mod:`harness_designer.ui.prop_ctrls.array_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _char_filter = None  # all characters allowed

    def __init__(self, parent, values, title='Modify Array'):
        """Initialise the :class:`ArrayStringDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param values: Values to store or process.
        :type values: UNKNOWN
        :param title: Value for ``title``.
        :type title: UNKNOWN
        """
        _ArrayDialog.__init__(self, parent, values, title)

    def GetValue(self) -> list:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list
        """
        return self._raw_values()


class ArrayStringProperty(QtWidgets.QWidget):
    """Represent an array string property in :mod:`harness_designer.ui.prop_ctrls.array_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label):
        """Initialise the :class:`ArrayStringProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        self._dialog_title = 'Enter Values'
        super().__init__(parent)
        self._value = []
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = QtWidgets.QLineEdit(self)
        self._ctrl.setReadOnly(True)
        self._button = QtWidgets.QPushButton('...', self)
        self._button.setFixedWidth(20)

        sizer = QtWidgets.QHBoxLayout(self)
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl, stretch=1)
        sizer.addWidget(self._button)

        self.setLayout(sizer)

        self._button.clicked.connect(self._on_dialog_button)

    def GetValue(self) -> list:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list
        """
        return self._value

    def SetValue(self, value: list):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list
        """
        self._value = value
        self._ctrl.setText(', '.join(value))

    def SetDialogTitle(self, value: str):
        """Execute the set dialog title operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._dialog_title = value

    def _on_dialog_button(self):
        """Handle the dialog button event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        dlg = ArrayStringDialog(self, self._value, self._dialog_title)
        dlg.adjustSize()
        dlg.move(self.mapToGlobal(self.rect().center()) - dlg.rect().center())
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            value = dlg.GetValue()
            if value == self._value:
                return

            self._value = value
            self._ctrl.setText(', '.join(value))

            evt = _events.PropertyEvent()
            evt.SetValue(self._value)
            evt.SetPropertyType(list)
            evt.SetProperty(self)
            self.propertyChanged.emit(evt)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
