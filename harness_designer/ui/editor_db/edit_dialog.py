# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDialogButtonBox

from ..dialogs import dialog_base as _dialog_base


if TYPE_CHECKING:
    from ... import ui as _ui


class EditDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.MainFrame", title, db_obj):
        super().__init__(parent, title=title, button_ids=QDialogButtonBox.Ok)

        control = db_obj.table.control
        control.setParent(self.panel)

        hsizer = QHBoxLayout()
        vsizer = QVBoxLayout()
        hsizer.addWidget(control, 1)
        vsizer.addLayout(hsizer, 1)

        self.panel.setLayout(vsizer)

        control.set_obj(db_obj)
        self.control = control
        self.db_obj = db_obj
        self.mainframe = parent

    def Destroy(self):
        self.control.set_obj(None)
        self.control.setParent(self.mainframe)
        self.control.hide()
        super().deleteLater()
