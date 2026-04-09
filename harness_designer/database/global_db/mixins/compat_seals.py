
from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


if TYPE_CHECKING:
    from .. import seal as _seal


class CompatSealsMixin(BaseMixin):

    @property
    def compat_seals(self) -> list["_seal.Seal"]:
        compat_seals = eval(self._table.select('compat_seals', id=self._db_id)[0][0])
        res = []
        for part_number in compat_seals:
            try:
                res.append(self._table.db.seals_table[part_number])
            except KeyError:
                pass
        return res

    @compat_seals.setter
    def compat_seals(self, value: list["_seal.Seal"]):
        compat_seals = [seal.part_number for seal in value]
        self._table.update(self._db_id, compat_seals=str(compat_seals))

    @property
    def compat_seals_array(self) -> list[str]:
        return eval(self._table.select('compat_seals', id=self._db_id)[0][0])

    @compat_seals_array.setter
    def compat_seals_array(self, value: list[str]):
        self._table.update(self._db_id, compat_seals=str(value))

    @property
    def _compat_seals_propgrid(self) -> _prop_grid.Property:

        prop = _prop_grid.ArrayStringProperty(
            'Compatible Seals', 'compat_seals_array', self.compat_seals_array)

        return prop
