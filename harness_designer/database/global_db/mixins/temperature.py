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

    @property
    def _temperature_propgrid(self) -> _prop_grid.Property:

        group_prop = _prop_grid.Property('Temperatures', '')

        min_temp_prop = self.min_temp.propgrid
        max_temp_prop = self.max_temp.propgrid
        min_temp_prop.SetLabel('Minimum')
        max_temp_prop.SetLabel('Maximum')

        group_prop.Append(min_temp_prop)
        group_prop.Append(max_temp_prop)

        return group_prop
