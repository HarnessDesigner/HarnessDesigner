from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import DescriptionMixin


class AdhesivesTable(TableBase):
    __table_name__ = 'adhesives'

    def __iter__(self) -> _Iterable["Adhesive"]:
        for db_id in TableBase.__iter__(self):
            yield Adhesive(self, db_id)

    def __getitem__(self, item) -> "Adhesive":
        if isinstance(item, int):
            if item in self:
                return Adhesive(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', code=item)
        if db_id:
            return Adhesive(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, code: str, description: str) -> "Adhesive":
        db_id = TableBase.insert(self, code=code, description=description)
        return Adhesive(self, db_id)


class Adhesive(EntryBase, DescriptionMixin):
    _table: AdhesivesTable = None

    @property
    def code(self) -> str:
        return self._table.select('code', id=self._db_id)[0][0]

    @code.setter
    def code(self, value: str):
        self._table.update(self._db_id, code=value)

    @property
    def accessories(self) -> list["_accessory.Accessory"]:
        accessory_nums = eval(self._table.select('accessory_part_nums', id=self._db_id)[0][0])
        res = []
        for part_number in accessory_nums:
            try:
                res.append(self._table.db.accessories_table[part_number])
            except KeyError:
                pass

        return res

    @accessories.setter
    def accessories(self, value: list["_accessory.Accessory"] | list[str]):
        part_numbers = [accessory if isinstance(accessory, str) else accessory.part_number for accessory in value]

        self._table.update(self._db_id, accessory_part_nums=str(part_numbers))


from . import accessory as _accessory  # NOQA
