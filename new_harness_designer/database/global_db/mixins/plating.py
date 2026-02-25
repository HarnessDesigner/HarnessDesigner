from typing import TYPE_CHECKING

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import plating as _plating


class PlatingMixin(BaseMixin):

    @property
    def plating(self) -> "_plating.Plating":
        plating_id = self.plating_id
        return self._table.db.platings_table[plating_id]

    @plating.setter
    def plating(self, value: "_plating.Plating"):
        self.plating_id = value.db_id

    @property
    def plating_id(self) -> int:
        return self._table.select('plating_id', id=self._db_id)[0][0]

    @plating_id.setter
    def plating_id(self, value: int):
        self._table.update(self._db_id, plating_id=value)
