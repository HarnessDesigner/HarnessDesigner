from typing import TYPE_CHECKING

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import sealing as _sealing  # NOQA


class SealingMixin(BaseMixin):

    @property
    def sealing(self) -> "_sealing.Sealing":
        from .. import sealing as _sealing  # NOQA

        sealing_id = self._table.select('sealing_id', id=self._db_id)
        return _sealing.Sealing(self._table.db.sealings_table, sealing_id[0][0])

    @sealing.setter
    def sealing(self, value: "_sealing.Sealing"):
        self._table.update(self._db_id, sealing_id=value.db_id)

    @property
    def sealing_id(self) -> int:
        return self._table.select('sealing_id', id=self._db_id)[0][0]

    @sealing_id.setter
    def sealing_id(self, value: int):
        self._table.update(self._db_id, sealing_id=value)
