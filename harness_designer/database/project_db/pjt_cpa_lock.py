from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import Angle3DMixin, Position3DMixin, PartMixin, HousingMixin, Visible3DMixin, NameMixin


if TYPE_CHECKING:
    from ..global_db import cpa_lock as _cpa_lock

    from ...objects import cpa_lock as _cpa_lock_obj


class PJTCPALocksTable(PJTTableBase):
    __table_name__ = 'pjt_cpa_locks'

    def _table_needs_update(self) -> bool:
        from ..create_database import cpa_locks

        return cpa_locks.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import cpa_locks

        cpa_locks.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import cpa_locks

        cpa_locks.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTCPALock"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTCPALock(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCPALock":
        if isinstance(item, int):
            if item in self:
                return PJTCPALock(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int | None) -> "PJTCPALock":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTCPALock(self, db_id, self.project_id)


class PJTCPALock(PJTEntryBase, Angle3DMixin, Position3DMixin,
                 PartMixin, HousingMixin, Visible3DMixin, NameMixin):

    _table: PJTCPALocksTable = None

    def get_object(self) -> "_cpa_lock_obj.CPALock":
        return self._obj

    def set_object(self, obj: "_cpa_lock_obj.CPALock"):
        self._obj = obj

    @property
    def table(self) -> PJTCPALocksTable:
        return self._table

    @property
    def part(self) -> "_cpa_lock.CPALock":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.cpa_locks_table[part_id]
