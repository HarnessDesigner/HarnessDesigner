from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import DescriptionMixin


class PlatingsTable(TableBase):
    __table_name__ = 'platings'

    def __iter__(self) -> _Iterable["Plating"]:

        for db_id in TableBase.__iter__(self):
            yield Plating(self, db_id)

    def __getitem__(self, item) -> "Plating":
        if isinstance(item, int):
            if item in self:
                return Plating(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', symbol=item)
        if db_id:
            return Plating(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, symbol: str, description: str) -> "Plating":
        db_id = TableBase.insert(self, symbol=symbol, description=description)
        return Plating(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT symbol FROM {self.__table_name__};')]


class Plating(EntryBase, DescriptionMixin):
    _table: PlatingsTable = None

    @property
    def symbol(self) -> str:
        return self._table.select('symbol', id=self._db_id)[0][0]

    @symbol.setter
    def symbol(self, value: str):
        self._table.update(self._db_id, symbol=value)
