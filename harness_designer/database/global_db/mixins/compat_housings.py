from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


if TYPE_CHECKING:
    from .. import housing as _housing


class CompatHousingsMixin(BaseMixin):

    @property
    def compat_housings(self) -> list["_housing.Housing"]:
        housings = eval(self._table.select('compat_housings', id=self._db_id)[0][0])
        res = []
        for part_number in housings:
            try:
                res.append(self._table.db.housings_table[part_number])
            except KeyError:
                pass
        return res

    @compat_housings.setter
    def compat_housings(self, value: list["_housing.Housing"]):
        mates_to = [housing.part_number for housing in value]
        self._table.update(self._db_id, compat_housings=str(mates_to))

    @property
    def compat_housings_array(self) -> list[str]:
        return eval(self._table.select('compat_housings', id=self._db_id)[0][0])

    @compat_housings_array.setter
    def compat_housings_array(self, value: list[str]):
        self._table.update(self._db_id, compat_housings=str(value))

    @property
    def _compat_housings_propgrid(self) -> _prop_grid.Property:

        prop = _prop_grid.ArrayStringProperty(
            'Compatible Housings', 'compat_housings_array', self.compat_housings_array)

        return prop
