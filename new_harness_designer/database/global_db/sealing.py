from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin


class SealingsTable(TableBase):
    __table_name__: str = 'sealings'

    def __iter__(self) -> _Iterable["Sealing"]:
        for db_id in TableBase.__iter__(self):
            yield Sealing(self, db_id)

    def __getitem__(self, item) -> "Sealing":
        if isinstance(item, int):
            if item in self:
                return Sealing(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Sealing(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "Sealing":

        db_id = TableBase.insert(self, name=name)
        return Sealing(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Sealing(EntryBase, NameMixin):
    _table: SealingsTable = None
