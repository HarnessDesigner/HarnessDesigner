
from typing import TYPE_CHECKING

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import cavity_lock as _cavity_lock  # NOQA


class CavityLockMixin(BaseMixin):

    @property
    def cavity_lock(self) -> "_cavity_lock.CavityLock":
        from ..cavity_lock import CavityLock
        lock_id = self.cavity_lock_id

        return CavityLock(self._table.db.cavity_locks_table, lock_id)

    @cavity_lock.setter
    def cavity_lock(self, value: "_cavity_lock.CavityLock"):
        self._table.update(self._db_id, cavity_lock_id=value.db_id)

    @property
    def cavity_lock_id(self) -> int:
        return self._table.select('cavity_lock_id', id=self._db_id)[0][0]

    @cavity_lock_id.setter
    def cavity_lock_id(self, value: int):
        self._table.update(self._db_id, cavity_lock_id=value)
