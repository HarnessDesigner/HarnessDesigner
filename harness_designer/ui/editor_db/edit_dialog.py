# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDialogButtonBox

from ..dialogs import dialog_base as _dialog_base


if TYPE_CHECKING:
    from ... import ui as _ui


class EditDialog(_dialog_base.BaseDialog):
    """Represent an edit dialog in :mod:`harness_designer.ui.editor_db.edit_dialog`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_ui.MainFrame", title, db_obj):
        """Initialise the :class:`EditDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param title: Value for ``title``.
        :type title: UNKNOWN
        :param db_obj: Database-backed object.
        :type db_obj: UNKNOWN
        """
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
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.control.set_obj(None)
        self.control.setParent(self.mainframe)
        self.control.hide()
        super().deleteLater()
