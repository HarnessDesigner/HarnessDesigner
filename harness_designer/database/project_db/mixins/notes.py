from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


class NotesMixin(BaseMixin):

    @property
    def notes(self) -> str:
        return self._table.select('notes', id=self._db_id)[0][0]

    @notes.setter
    def notes(self, value: str):
        self._table.update(self._db_id, notes=value)
        self._populate('notes')


class NotesControl(_prop_ctrls.LongStringProperty):

    def __init__(self, parent):
        self.db_obj: NotesMixin = None

        super().__init__(parent, 'Notes')

        self.Bind(_prop_ctrls.EVT_PROPERTY_CHANGED, self._on_notes)

    def _on_notes(self, evt):
        value = evt.GetValue()
        self.db_obj.notes = value

    def set_obj(self, db_obj: NotesMixin):
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue('')
            self.Enable(False)
        else:
            self.SetValue(db_obj.notes)
            self.Enable(True)
