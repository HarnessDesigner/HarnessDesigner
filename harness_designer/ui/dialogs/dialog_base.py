# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt

from . import header as _header


class BaseDialog(QDialog):

    def __init__(self, parent, title, size=(-1, -1),
                 style=None, button_ids=None):

        flags = (Qt.Dialog | Qt.WindowStaysOnTopHint |
                 Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        super().__init__(parent, flags)

        w, h = size
        if w != -1 or h != -1:
            self.resize(
                w if w != -1 else self.sizeHint().width(),
                h if h != -1 else self.sizeHint().height()
            )

        self.panel = QWidget(self)
        self.header = _header.Header(self, title)

        if button_ids is None:
            button_ids = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.button_box = QDialogButtonBox(button_ids, parent=self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)

        root = QVBoxLayout(self)
        root.setContentsMargins(5, 10, 5, 10)
        root.setSpacing(0)
        root.addWidget(self.header)
        root.addSpacing(5)
        root.addWidget(self.panel, 1)
        root.addSpacing(5)
        root.addWidget(sep)
        root.addSpacing(5)
        root.addWidget(self.button_box)

        if parent is not None:
            self.adjustSize()
            self.move(
                parent.mapToGlobal(parent.rect().center()) -
                self.rect().center()
            )

    def GetValue(self):
        raise NotImplementedError
