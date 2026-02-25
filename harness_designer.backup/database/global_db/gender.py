from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin


class GendersTable(TableBase):
    __table_name__ = 'genders'

    def __iter__(self) -> _Iterable["Gender"]:
        for db_id in TableBase.__iter__(self):
            yield Gender(self, db_id)

    def __getitem__(self, item) -> "Gender":
        if isinstance(item, int):
            if item in self:
                return Gender(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Gender(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "Gender":
        db_id = TableBase.insert(self, name=name)
        return Gender(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Gender(EntryBase, NameMixin):
    _table: GendersTable = None
