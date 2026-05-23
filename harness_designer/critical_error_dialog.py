# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog helpers for reporting critical startup errors."""

import traceback
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QPushButton, QStyle, QDialogButtonBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt


class CriticalErrorDialog(QDialog):
    """Display an exception and issue-reporting instructions to the user."""

    def __init__(self, parent, err):
        """Build the critical error dialog.

        :param parent: Parent widget for the dialog.
        :type parent: PySide6.QtWidgets.QWidget | None
        :param err: Exception to display.
        :type err: BaseException
        """
        super().__init__(parent)

        message = ''.join(traceback.format_exception(err))

        caption_text = (
            'A critical error has occured...\n\n'
            'Please report this error to\n'
            'https://github.com/HarnessDesigner/HarnessDesigner/issues\n'
        )

        self.setWindowTitle('Critical Error')
        self.resize(400, 600)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.Dialog |
            Qt.WindowCloseButtonHint |
            Qt.WindowTitleHint
        )

        # Error icon from the platform style
        style = self.style()
        icon_pixmap = style.standardIcon(QStyle.SP_MessageBoxCritical).pixmap(32, 32)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)

        caption_label = QLabel(caption_text)
        caption_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        header_layout = QHBoxLayout()
        header_layout.addWidget(icon_label)
        header_layout.addWidget(caption_label)
        header_layout.addStretch()

        err_msg = QTextEdit()
        err_msg.setPlainText(message)
        err_msg.setReadOnly(True)
        err_msg.setLineWrapMode(QTextEdit.NoWrap)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(header_layout)
        layout.addWidget(err_msg)
        layout.addWidget(button_box)

        self.setLayout(layout)
