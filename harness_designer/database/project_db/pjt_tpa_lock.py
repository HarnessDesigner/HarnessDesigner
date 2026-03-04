from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase

from .mixins import (Angle3DMixin, Position3DMixin, PartMixin,
                     HousingMixin, Visible3DMixin, NameMixin)


if TYPE_CHECKING:
    from ..global_db import tpa_lock as _tpa_lock

    from ...objects import tpa_lock as _tpa_lock_obj


class PJTTPALocksTable(PJTTableBase):
    __table_name__ = 'pjt_tpa_locks'

    def __iter__(self) -> _Iterable["PJTTPALock"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTPALock(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTPALock":
        if isinstance(item, int):
            if item in self:
                return PJTTPALock(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int | None) -> "PJTTPALock":
        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id)

        return PJTTPALock(self, db_id, self.project_id)


class PJTTPALock(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin,
                 HousingMixin, Visible3DMixin, NameMixin):

    _table: PJTTPALocksTable = None

    def get_object(self) -> "_tpa_lock_obj.TPALock":
        return self._obj

    def set_object(self, obj: "_tpa_lock_obj.TPALock"):
        self._obj = obj

    @property
    def table(self) -> PJTTPALocksTable:
        return self._table

    @property
    def part(self) -> "_tpa_lock.TPALock":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.cpa_locks_table[part_id]
