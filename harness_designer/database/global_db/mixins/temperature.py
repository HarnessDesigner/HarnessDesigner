from typing import TYPE_CHECKING

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
