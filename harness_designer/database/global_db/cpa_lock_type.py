from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class CPALockTypesTable(TableBase):
    __table_name__ = 'cpa_lock_types'

    def _table_needs_update(self) -> bool:
        from ..create_database import cpa_lock_types

        return cpa_lock_types.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import cpa_lock_types

        cpa_lock_types.table.add_to_db(self)
        cpa_lock_types.add_records(self._con, splash)

    def _update_table_in_db(self):
        from ..create_database import cpa_lock_types

        cpa_lock_types.table.update_fields(self)

    def __iter__(self) -> _Iterable["CPALockType"]:
        for db_id in TableBase.__iter__(self):
            yield CPALockType(self, db_id)

    def __getitem__(self, item) -> "CPALockType":
        if isinstance(item, int):
            if item in self:
                return CPALockType(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return CPALockType(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "CPALockType":
        db_id = TableBase.insert(self, name=name)
        return CPALockType(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class CPALockType(EntryBase, NameMixin):
    _table: CPALockTypesTable = None
