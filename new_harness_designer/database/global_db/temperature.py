from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin


class TemperaturesTable(TableBase):
    __table_name__ = 'temperatures'

    def __iter__(self) -> _Iterable["Temperature"]:
        for db_id in TableBase.__iter__(self):
            yield Temperature(self, db_id)

    def __getitem__(self, item) -> "Temperature":
        if isinstance(item, int):
            if item in self:
                return Temperature(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Temperature(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "Temperature":
        db_id = TableBase.insert(self, name=name)
        return Temperature(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Temperature(EntryBase, NameMixin):
    _table: TemperaturesTable = None
