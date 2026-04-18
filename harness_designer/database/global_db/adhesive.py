from typing import Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import DescriptionMixin


class AdhesivesTable(TableBase):
    __table_name__ = 'adhesives'

    def _table_needs_update(self) -> bool:
        from ..create_database import adhesives

        return adhesives.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import adhesives

        adhesives.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        adhesives.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import adhesives

        adhesives.table.update_fields(self)

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

    def build_monitor_packet(self):
        packet = {
            'adhesives': [self.db_id],
        }

        return packet

    @property
    def code(self) -> str:
        return self._table.select('code', id=self._db_id)[0][0]

    @code.setter
    def code(self, value: str):
        self._table.update(self._db_id, code=value)
        self._populate('code')

    @property
    def accessory_part_nums(self) -> list[str]:
        part_nums = self._table.select('accessory_part_nums', id=self._db_id)[0][0]
        part_nums = part_nums[1:-1].split(', ')
        return part_nums

    @accessory_part_nums.setter
    def accessory_part_nums(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, accessory_part_nums=value)
        self._populate('accessory_part_nums')

    @property
    def accessories(self) -> list["_accessory.Accessory"]:
        accessory_nums = eval(self._table.select('accessory_part_nums',
                                                 id=self._db_id)[0][0])
        res = []
        for part_number in accessory_nums:
            try:
                res.append(self._table.db.accessories_table[part_number])
            except KeyError:
                pass

        return res


from . import accessory as _accessory  # NOQA
