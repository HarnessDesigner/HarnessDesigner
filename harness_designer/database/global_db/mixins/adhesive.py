from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid
from .base import BaseMixin


if TYPE_CHECKING:
    from .. import adhesive as _adhesive  # NOQA


class AdhesiveMixin(BaseMixin):

    @property
    def adhesives(self) -> list["_adhesive.Adhesive"]:
        ids = eval(self._table.select('adhesive_ids', id=self._db_id)[0][0])
        res = []

        for db_id in ids:
            try:
                res.append(self._table.db.adhesives_table[db_id])
            except IndexError:
                continue

        return res

    @property
    def adhesive_ids(self) -> list[str]:
        return eval(self._table.select('adhesive_ids', id=self._db_id)[0][0])

    @adhesive_ids.setter
    def adhesive_ids(self, value: list[str]):
        self._table.update(self._db_id, adhesive_ids=str(value))


class AdhesiveControl(_prop_grid.ArrayStringProperty):

    def __init__(self, parent):
        self.db_obj: AdhesiveMixin = None

        super().__init__(parent, 'Adhesives', [])

    def _on_adhesives(self, evt):
        value = evt.GetValue()
        self.db_obj.adhesive_ids = value

    def set_obj(self, db_obj: AdhesiveMixin):
        self.db_obj = db_obj
        self.SetValue(db_obj.adhesive_ids)
