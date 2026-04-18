from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class TemperaturesTable(TableBase):
    __table_name__ = 'temperatures'

    def _table_needs_update(self) -> bool:
        from ..create_database import temperatures

        return temperatures.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import temperatures

        temperatures.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        temperatures.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import temperatures

        temperatures.table.update_fields(self)

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

    def build_monitor_packet(self):
        packet = {
            'temperatures': [self.db_id],
        }

        return packet
