# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin
from ....ui import prop_ctrls as _prop_ctrls
from .... import check_types as _check_types


if TYPE_CHECKING:
    from ....ui.prop_ctrls import events as _prop_events
    from PySide6 import QtWidgets


class NotesMixin(BaseMixin):
    """Represent a notes mixin in :mod:`harness_designer.database.project_db.mixins.notes`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    @property
    @_check_types.do
    def notes(self) -> str:
        """Return the notes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        _rows = self._table.select('notes', id=self._db_id)
        return _rows[0][0] if _rows else None

    @notes.setter
    @_check_types.do
    def notes(self, value: str) -> None:
        """Set the notes.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, notes=value)
        self._populate('notes')


class NotesControl(_prop_ctrls.LongStringProperty):
    """Represent a notes control in :mod:`harness_designer.database.project_db.mixins.notes`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget") -> None:
        """Initialise the :class:`NotesControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: NotesMixin | None = None

        super().__init__(parent, 'Notes')

        self.propertyChanged.connect(self._on_notes)

    @_check_types.do
    def _on_notes(self, evt: "_prop_events.PropertyEvent") -> None:
        """Handle the notes event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.notes = value

    @_check_types.do
    def set_obj(self, db_obj: NotesMixin | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`NotesMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue('')
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.notes)
            self.setEnabled(True)
