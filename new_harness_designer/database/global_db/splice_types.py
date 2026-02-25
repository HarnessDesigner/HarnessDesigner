from typing import Iterable as _Iterable

from .import EntryBase, TableBase
from .mixins import NameMixin


class SpliceTypesTable(TableBase):
    __table_name__ = 'splice_types'

    def __iter__(self) -> _Iterable["SpliceType"]:
        for db_id in TableBase.__iter__(self):
            yield SpliceType(self, db_id)

    def __getitem__(self, item) -> "SpliceType":
        if isinstance(item, int):
            if item in self:
                return SpliceType(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return SpliceType(self, db_id[0][0])

        raise KeyError(item)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str) -> "SpliceType":
        db_id = TableBase.insert(self, name=name)
        return SpliceType(self, db_id)


class SpliceType(EntryBase, NameMixin):
    _table: SpliceTypesTable = None
