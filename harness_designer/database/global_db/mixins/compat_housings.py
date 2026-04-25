from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


if TYPE_CHECKING:
    from .. import housing as _housing


class CompatHousingsMixin(BaseMixin):

    @property
    def compat_housings(self) -> list["_housing.Housing"]:
        housings = self.compat_housings_array
        res = []
        for part_number in housings:
            try:
                res.append(self._table.db.housings_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_housings_array(self) -> list[str]:
        value = self._table.select('compat_housings', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_housings_array.setter
    def compat_housings_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_housings=value)
        self._populate('compat_housings_array')


class CompatHousingsControl(_prop_grid.ArrayStringProperty):

    def __init__(self, parent):
        self.db_obj: CompatHousingsMixin = None
        super().__init__(parent, 'Compatible Housings')

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_housings)

    def set_obj(self, db_obj: CompatHousingsMixin):
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue([])
            self.Enable(False)
        else:
            self.SetValue(db_obj.compat_housings_array)
            self.Enable(True)

    def _on_compat_housings(self, evt: _prop_grid.PropertyEvent):
        compat_housings = evt.GetValue()
        self.db_obj.compat_seals_array = compat_housings
