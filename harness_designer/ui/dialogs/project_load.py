# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QProgressDialog
from PySide6.QtCore import Qt


class ProjectLoadDialog(QProgressDialog):

    def __init__(self, parent):
        super().__init__('', None, 0, 100, parent,
                         Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setWindowTitle('Project Loading...')
        self.setMinimumDuration(0)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setValue(0)

        if parent is not None:
            self.move(
                parent.mapToGlobal(parent.rect().center()) -
                self.rect().center()
            )

    def Update(self, value, newmsg=''):
        max_val = self.maximum()
        msg = f'{newmsg}     {value}[{max_val}]'
        self.setLabelText(msg)
        self.setValue(value)
