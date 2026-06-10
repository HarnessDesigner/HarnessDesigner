# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import events as _events


class LongStringDialog(QtWidgets.QDialog):
    """Represent a long string dialog in :mod:`harness_designer.ui.prop_ctrls.long_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, value: str, title: str = 'Enter Text'):
        """Initialise the :class:`LongStringDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param value: Value to store or process.
        :type value: str
        :param title: Value for ``title``.
        :type title: str
        """
        QtWidgets.QDialog.__init__(
            self, parent,
            QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint | QtCore.Qt.WindowType.WindowTitleHint
        )
        self.setWindowTitle(title)
        self.resize(300, 200)
        self.setSizeGripEnabled(True)

        self.ctrl = QtWidgets.QTextEdit(self)
        self.ctrl.setPlainText(value)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel, self)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        sep = QtWidgets.QFrame(self)
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ctrl, stretch=1)
        layout.addWidget(sep)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.ctrl.toPlainText()


class LongStringProperty(QtWidgets.QWidget):
    """Represent a long string property in :mod:`harness_designer.ui.prop_ctrls.long_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str, style: int = 0, units: str | None = None):
        """Initialise the :class:`LongStringProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        :param style: Value for ``style``.
        :type style: `int`
        :param units: Value for ``units``.
        :type units: `str | None`
        """

        super().__init__(parent)

        self._dialog_title = 'Enter Text'
        self._value = ''
        self._label = label

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = QtWidgets.QLineEdit(self)
        self._ctrl.setReadOnly(True)
        self._button = QtWidgets.QPushButton('...', self)
        self._button.setFixedWidth(20)

        self._units_st = None
        if units is not None:
            self._units_st = QtWidgets.QLabel(units, self)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)

        sizer.addWidget(self._st)
        sizer.addWidget(self._ctrl, stretch=1)
        sizer.addWidget(self._button)

        if self._units_st:
            sizer.addWidget(
                self._units_st, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        self.setLayout(sizer)
        self._button.clicked.connect(self._on_dialog_button)

    def SetDialogTitle(self, value: str) -> None:
        """
        Execute the set dialog title operation.

        :param value: Value to store or process.
        :type value: str
        """

        self._dialog_title = value

    def GetValue(self) -> str:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """

        return self._value

    def SetValue(self, value: str) -> None:
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: str
        """

        self._value = value
        self._ctrl.blockSignals(True)

        self._ctrl.setText(value)

        self._ctrl.blockSignals(False)

    def _on_dialog_button(self) -> None:
        """
        Handle the dialog button event.
        """
        dlg = LongStringDialog(self, self._value, self._dialog_title)
        dlg.adjustSize()
        dlg.move(self.mapToGlobal(self.rect().center()) - dlg.rect().center())

        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            value = dlg.GetValue()
            if value == self._value:
                return

            self._value = value
            self._ctrl.setText(value)

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
