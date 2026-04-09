from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import pjt_housing as _pjt_housing


class HousingMixin(BaseMixin):

    @property
    def housing(self) -> "_pjt_housing.PJTHousing":
        db_id = self.housing_id
        if db_id is None:
            return None

        return self._table.db.pjt_housings_table[db_id]

    @property
    def housing_id(self) -> int:
        return self._table.select('housing_id', id=self._db_id)[0][0]

    @housing_id.setter
    def housing_id(self, value: int):
        self._table.update(self._db_id, housing_id=value)

    @property
    def _housing_propgrid(self) -> _prop_grid.Property:
        prop = _prop_grid.StringProperty('Housing', 'housing', self.housing.part.part_number)
        return prop
