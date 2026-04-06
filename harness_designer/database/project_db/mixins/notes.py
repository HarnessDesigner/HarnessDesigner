from .base import BaseMixin

from wx import propgrid as wxpg


class NotesMixin(BaseMixin):

    @property
    def notes(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @notes.setter
    def notes(self, value: str):
        self._table.update(self._db_id, name=value)

    @property
    def _notes_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import long_string_prop as _long_string_prop

        notes_prop = _long_string_prop.LongStringProperty('Notes', 'notes', self.notes)

        return notes_prop