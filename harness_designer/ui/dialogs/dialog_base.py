# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import header as _header

if TYPE_CHECKING:
    from ... import ui as _ui


class BaseDialog(QtWidgets.QDialog):

    def __init__(self, parent: "_ui.MainFrame", title: str, size=(-1, -1),
                 style=None, button_ids=None):

        self.mainframe = parent

        flags = (QtCore.Qt.WindowType.Dialog |
                 QtCore.Qt.WindowType.WindowStaysOnTopHint |
                 QtCore.Qt.WindowType.WindowCloseButtonHint |
                 QtCore.Qt.WindowType.WindowTitleHint)

        if style is not None:
            flags |= style

        super().__init__(parent, flags)

        w, h = size
        if w != -1 or h != -1:
            self.resize(
                w if w != -1 else self.sizeHint().width(),
                h if h != -1 else self.sizeHint().height()
            )

        self.panel = QtWidgets.QWidget(self)
        self.header = _header.Header(self, title)

        if button_ids is None:
            button_ids = (QtWidgets.QDialogButtonBox.StandardButton.Ok |
                          QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        self.button_box = QtWidgets.QDialogButtonBox(button_ids, parent=self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        sep = QtWidgets.QFrame(self)
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        root = QtWidgets.QVBoxLayout(self)
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
            self.move(parent.mapToGlobal(
                parent.rect().center()) - self.rect().center())

    def GetValue(self):
        raise NotImplementedError
