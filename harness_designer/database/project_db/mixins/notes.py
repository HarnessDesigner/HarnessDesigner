# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....ui import prop_ctrls as _prop_ctrls


class NotesMixin(BaseMixin):
    """Represent a notes mixin in :mod:`harness_designer.database.project_db.mixins.notes`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_notes: str | DefaultStoredValueType = DefaultStoredValue

    @property
    def notes(self) -> str:
        """Return the notes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_notes is DefaultStoredValue:
            self._stored_notes = self._table.select('notes', id=self._db_id)[0][0]
            
        return self._stored_notes

    @notes.setter
    def notes(self, value: str):
        """Set the notes.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_notes = value
        self._table.update(self._db_id, notes=value)
        self._populate('notes')


class NotesControl(_prop_ctrls.LongStringProperty):
    """Represent a notes control in :mod:`harness_designer.database.project_db.mixins.notes`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`NotesControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: NotesMixin = None

        super().__init__(parent, 'Notes')

        self.propertyChanged.connect(self._on_notes)

    def _on_notes(self, evt):
        """Handle the notes event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.notes = value

    def set_obj(self, db_obj: NotesMixin):
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
