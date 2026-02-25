
from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class CavityLocksTable(TableBase):
    __table_name__ = 'cavity_locks'

    def __iter__(self) -> _Iterable["CavityLock"]:
        for db_id in TableBase.__iter__(self):
            yield CavityLock(self, db_id)

    def __getitem__(self, item) -> "CavityLock":
        if isinstance(item, int):
            if item in self:
                return CavityLock(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return CavityLock(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, description: str) -> "CavityLock":
        db_id = TableBase.insert(self, name=name, description=description)
        return CavityLock(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class CavityLock(EntryBase, NameMixin, DescriptionMixin):
    _table: CavityLocksTable = None
