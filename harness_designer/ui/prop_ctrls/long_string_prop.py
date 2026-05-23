# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QDialog, QTextEdit, QLineEdit, QPushButton,
    QDialogButtonBox, QLabel, QHBoxLayout, QVBoxLayout, QFrame
)
from PySide6.QtCore import Qt

from . import prop_base as _prop_base


class LongStringDialog(QDialog):
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
        QDialog.__init__(
            self, parent,
            Qt.Dialog | Qt.WindowStaysOnTopHint |
            Qt.WindowCloseButtonHint | Qt.WindowTitleHint
        )
        self.setWindowTitle(title)
        self.resize(300, 200)
        self.setSizeGripEnabled(True)

        self.ctrl = QTextEdit(self)
        self.ctrl.setPlainText(value)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)

        layout = QVBoxLayout(self)
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


class LongStringProperty(_prop_base.Property):
    """Represent a long string property in :mod:`harness_designer.ui.prop_ctrls.long_string_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label, style=0, units=None):
        """Initialise the :class:`LongStringProperty` instance.

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
        _prop_base.Property.__init__(self, parent, label)
        self._dialog_title = 'Enter Text'
        self._value = ''

        self._st = QLabel(label + ':', self)
        self._ctrl = QLineEdit(self)
        self._ctrl.setReadOnly(True)
        self._button = QPushButton('...', self)
        self._button.setFixedWidth(20)

        self._units_st = None
        if units is not None:
            self._units_st = QLabel(units, self)

        inner_row = QHBoxLayout()
        inner_row.setContentsMargins(0, 0, 0, 0)
        inner_row.addWidget(self._ctrl, stretch=1)
        inner_row.addWidget(self._button)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.addLayout(inner_row)
        row.addLayout(col, stretch=1)

        if self._units_st:
            row.addWidget(self._units_st, alignment=Qt.AlignBottom)

        self._sizer.addLayout(row)
        self._button.clicked.connect(self._on_dialog_button)

    def SetDialogTitle(self, value: str):
        """Execute the set dialog title operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._dialog_title = value

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

    def _on_dialog_button(self):
        """Handle the dialog button event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        dlg = LongStringDialog(self, self._value, self._dialog_title)
        dlg.adjustSize()
        dlg.move(
            self.mapToGlobal(self.rect().center()) - dlg.rect().center()
        )
        if dlg.exec() == QDialog.Accepted:
            value = dlg.GetValue()
            if value == self._value:
                return
            self._value = value
            self._ctrl.setText(value)
            self._send_changed_event(str, value)
