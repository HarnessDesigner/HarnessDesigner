from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import gender as _gender  # NOQA


class GenderMixin(BaseMixin):

    @property
    def gender(self) -> "_gender.Gender":
        from .. import gender as _gender  # NOQA

        gender_id = self._table.select('gender_id', id=self._db_id)
        return _gender.Gender(self._table.db.genders_table, gender_id[0][0])

    @gender.setter
    def gender(self, value: "_gender.Gender"):
        self._table.update(self._db_id, gender_id=value.db_id)

    @property
    def gender_id(self) -> int:
        return self._table.select('gender_id', id=self._db_id)[0][0]

    @gender_id.setter
    def gender_id(self, value: int):
        self._table.update(self._db_id, gender_id=value)


class GenderControl(_prop_grid.ComboBoxProperty):

    def __init__(self, parent):

        self.choices: list[str] = []
        self.db_obj: GenderMixin = None

        super().__init__(parent, 'Gender', '', [])
        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_gender)

    def set_obj(self, db_obj: GenderMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems(self.choices)
            self.SetValue('')
            self.Enable(False)
        else:
            db_obj.table.execute('SELECT name FROM genders;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.gender.name)
            self.Enable(True)

    def _on_gender(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM genders WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.genders_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.gender_id = db_id
