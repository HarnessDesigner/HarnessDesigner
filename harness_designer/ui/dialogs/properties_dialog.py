
from PySide6 import QtWidgets

from . import dialog_base as _dialog_base


class PropertiesDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, title, tab_widget, db_obj):
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
