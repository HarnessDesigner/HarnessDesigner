
from typing import TYPE_CHECKING

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

    @adhesives.setter
    def adhesives(self, value: list["_adhesive.Adhesive"]):
        value = [adhesive.db_id for adhesive in value]
        self._table.update(self._db_id, adhesive_ids=str(value))
