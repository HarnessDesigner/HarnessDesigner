
from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class MaterialsTable(TableBase):
    __table_name__ = 'materials'

    def __iter__(self) -> _Iterable["Material"]:
        for db_id in TableBase.__iter__(self):
            yield Material(self, db_id)

    def __getitem__(self, item) -> "Material":
        if isinstance(item, int):
            if item in self:
                return Material(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Material(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "Material":
        db_id = TableBase.insert(self, name=name)
        return Material(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Material(EntryBase, NameMixin, DescriptionMixin):
    _table: MaterialsTable = None
