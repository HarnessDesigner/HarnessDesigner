from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid
from .base import BaseMixin


if TYPE_CHECKING:
    from .. import temperature as _temperature  # NOQA


class TemperatureMixin(BaseMixin):

    @property
    def min_temp(self) -> "_temperature.Temperature":
        from .. import temperature as _temperature  # NOQA

        min_temp_id = self._table.select('min_temp_id', id=self._db_id)
        return _temperature.Temperature(self._table.db.temperatures_table, min_temp_id[0][0])

    @min_temp.setter
    def min_temp(self, value: "_temperature.Temperature"):
        self._table.update(self._db_id, min_temp_id=value.db_id)

    @property
    def min_temp_id(self) -> int:
        return self._table.select('min_temp_id', id=self._db_id)[0][0]

    @min_temp_id.setter
    def min_temp_id(self, value: int):
        self._table.update(self._db_id, min_temp_id=value)

    @property
    def max_temp(self) -> "_temperature.Temperature":
        from .. import temperature as _temperature  # NOQA

        max_temp_id = self._table.select('max_temp_id', id=self._db_id)
        return _temperature.Temperature(self._table.db.temperatures_table, max_temp_id[0][0])

    @max_temp.setter
    def max_temp(self, value: "_temperature.Temperature"):
        self._table.update(self._db_id, max_temp_id=value.db_id)

    @property
    def max_temp_id(self) -> int:
        return self._table.select('max_temp_id', id=self._db_id)[0][0]

    @max_temp_id.setter
    def max_temp_id(self, value: int):
        self._table.update(self._db_id, max_temp_id=value)


class TemperatureControl(_prop_grid.Category):

    def __init__(self, parent):
        super().__init__(parent, 'Temperatures')

        self.choices: list[str] = []
        self.db_obj: TemperatureMixin = None

        self.min_temp_ctrl = _prop_grid.ComboBoxProperty(self, 'Minimum', '', [])
        self.max_temp_ctrl = _prop_grid.ComboBoxProperty(self, 'Maximum', '', [])

        self.min_temp_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_temp)
        self.max_temp_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_temp)

    def set_obj(self, db_obj: TemperatureMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue('')
            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue('')
            self.min_temp_ctrl.Enable(False)
            self.max_temp_ctrl.Enable(False)
        else:
            min_temp = db_obj.min_temp
            max_temp = db_obj.max_temp

            db_obj.table.execute(f'SELECT name FROM temperatures;')
            rows = db_obj.table.fetchall()
            self.choices = sorted([row[0] for row in rows])

            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue(min_temp.name)
            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue(max_temp.name)

            self.min_temp_ctrl.Enable(True)
            self.max_temp_ctrl.Enable(True)

    def _on_min_temp(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.temperatures_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue(name)

            value = self.max_temp_ctrl.GetValue()
            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue(value)

        self.db_obj.min_temp_id = db_id

    def _on_max_temp(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.temperatures_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue(name)

            value = self.min_temp_ctrl.GetValue()
            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue(value)

        self.db_obj.max_temp_id = db_id
