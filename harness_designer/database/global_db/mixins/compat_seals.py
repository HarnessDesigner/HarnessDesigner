
from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


if TYPE_CHECKING:
    from .. import seal as _seal


class CompatSealsMixin(BaseMixin):

    @property
    def compat_seals(self) -> list["_seal.Seal"]:
        compat_seals = self.compat_seals_array
        res = []
        for part_number in compat_seals:
            try:
                res.append(self._table.db.seals_table[part_number])
            except KeyError:
                pass
        return res

    @compat_seals.setter
    def compat_seals(self, value: list["_seal.Seal"]):
        self.compat_seals_array = [seal.part_number for seal in value]

    @property
    def compat_seals_array(self) -> list[str]:
        value = self._table.select('compat_seals', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_seals_array.setter
    def compat_seals_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_seals=value)


class CompatSealsControl(_prop_grid.ArrayStringProperty):

    def __init__(self, parent):
        self.db_obj: CompatSealsMixin = None
        super().__init__(parent, 'Compatible Seals', [])

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_housings)

    def set_obj(self, db_obj: CompatSealsMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue([])
            self.Enable(False)
        else:
            self.SetValue(db_obj.compat_seals_array)
            self.Enable(True)

    def _on_compat_housings(self, evt: _prop_grid.PropertyEvent):
        compat_seals = evt.GetValue()
        self.db_obj.compat_seals_array = compat_seals
