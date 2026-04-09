from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class NotesMixin(BaseMixin):

    @property
    def notes(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @notes.setter
    def notes(self, value: str):
        self._table.update(self._db_id, name=value)

    @property
    def _notes_propgrid(self) -> _prop_grid.Property:

        notes_prop = _prop_grid.LongStringProperty('Notes', 'notes', self.notes)

        return notes_prop
