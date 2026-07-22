# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog helpers for reporting critical startup errors."""

import traceback
from PySide6 import QtWidgets
from PySide6 import QtCore


class CriticalErrorDialog(QtWidgets.QDialog):
    """Display an exception and issue-reporting instructions to the user."""

    def __init__(self, parent, err, title='Critical Error', context=None):
        """Build the critical error dialog.

        :param parent: Parent widget for the dialog.
        :type parent: PySide6.QtWidgets.QWidget | None
        :param err: Exception to display.
        :type err: BaseException
        :param title: Window title -- callers reporting a recoverable error
                      (e.g. a caught SQL error) rather than a fatal startup
                      failure should override this.
        :type title: str
        :param context: Optional extra text (e.g. the failing SQL statement
                        and its params) shown above the traceback.
        :type context: str | None
        """
        super().__init__(parent)

        message = ''.join(traceback.format_exception(err))
        if context:
            message = f'{context}\n\n{message}'

        caption_text = ('A critical error has occured...\n\n'
                        'Please report this error to\n'
                        'https://github.com/HarnessDesigner/HarnessDesigner/issues\n')

        self.setWindowTitle(title)
        self.resize(400, 600)
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Dialog |
            QtCore.Qt.WindowType.WindowCloseButtonHint |
            QtCore.Qt.WindowType.WindowTitleHint
        )

        # Error icon from the platform style
        style = self.style()
        icon_pixmap = style.standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_MessageBoxCritical).pixmap(32, 32)

        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(icon_pixmap)

        caption_label = QtWidgets.QLabel(caption_text)
        caption_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter |
                                   QtCore.Qt.AlignmentFlag.AlignLeft)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(icon_label)
        header_layout.addWidget(caption_label)
        header_layout.addStretch()

        err_msg = QtWidgets.QTextEdit()
        err_msg.setPlainText(message)
        err_msg.setReadOnly(True)
        err_msg.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)

        button_box.accepted.connect(self.accept)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(header_layout)
        layout.addWidget(err_msg)
        layout.addWidget(button_box)

        self.setLayout(layout)
