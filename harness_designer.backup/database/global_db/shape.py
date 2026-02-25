
from typing import Iterable as _Iterable

from .import EntryBase, TableBase
from .mixins import NameMixin


class ShapesTable(TableBase):
    __table_name__ = 'shapes'

    def __iter__(self) -> _Iterable["Shape"]:
        for db_id in TableBase.__iter__(self):
            yield Shape(self, db_id)

    def __getitem__(self, item) -> "Shape":
        if isinstance(item, int):
            if item in self:
                return Shape(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Shape(self, db_id[0][0])

        raise KeyError(item)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str) -> "Shape":
        db_id = TableBase.insert(self, name=name)
        return Shape(self, db_id)


class Shape(EntryBase, NameMixin):
    _table: ShapesTable = None
