from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import direction as _direction  # NOQA


class DirectionMixin(BaseMixin):

    @property
    def direction(self) -> "_direction.Direction":
        from .. import direction as _direction  # NOQA

        direction_id = self._table.select('direction_id', id=self._db_id)
        return _direction.Direction(self._table.db.directions_table, direction_id[0][0])

    @direction.setter
    def direction(self, value: "_direction.Direction"):
        self._table.update(self._db_id, direction_id=value.db_id)

    @property
    def direction_id(self) -> int:
        return self._table.select('direction_id', id=self._db_id)[0][0]

    @direction_id.setter
    def direction_id(self, value: int):
        self._table.update(self._db_id, direction_id=value)

    @property
    def _direction_propgrid(self) -> _prop_grid.Property:
        prop = self.direction.propgrid
        return prop


class DirectionControl(_prop_grid.ComboBoxProperty):

    def __init__(self, parent):

        self.choices: list[str] = []
        self.db_obj: DirectionMixin = None

        super().__init__(parent, 'Direction', '', [])
        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_direction)

    def set_obj(self, db_obj: DirectionMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems([])
            self.SetValue('')
            self.Enable(False)
        else:
            db_obj.table.execute('SELECT name FROM directions;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.direction.name)
            self.Enable(True)


    def _on_direction(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM directions WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.directions_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.direction_id = db_id
