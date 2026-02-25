from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin


class ProtectionsTable(TableBase):
    __table_name__ = 'protections'

    def __iter__(self) -> _Iterable["Protection"]:
        for db_id in TableBase.__iter__(self):
            yield Protection(self, db_id)

    def __getitem__(self, item) -> "Protection":
        if isinstance(item, int):
            if item in self:
                return Protection(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Protection(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "Protection":
        db_id = TableBase.insert(self, name=name)
        return Protection(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Protection(EntryBase, NameMixin):
    _table: ProtectionsTable = None
