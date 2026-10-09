
from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from . import dialog_base as _dialog_base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui
    from ...database.global_db import bases as _global_bases


class PropertiesDialog(_dialog_base.BaseDialog):

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", title: str,
                 tab_widget: QtWidgets.QWidget, db_obj: "_global_bases.EntryBase") -> None:
        super().__init__(parent, title, (500, 500),
                         button_ids=QtWidgets.QDialogButtonBox.StandardButton.Ok)

        tab_widget.setParent(self.panel)
        tab_widget.set_obj(db_obj)
        tab_widget.show()

        vsizer = QtWidgets.QVBoxLayout()
        hsizer = QtWidgets.QHBoxLayout()
        hsizer.addWidget(tab_widget, 1)
        vsizer.addLayout(hsizer, 1)
        self.panel.setLayout(vsizer)
