from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin, ManufacturerMixin


class SeriesTable(TableBase):
    __table_name__ = 'series'

    def _table_needs_update(self) -> bool:
        from ..create_database import series

        return series.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import series

        series.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        series.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import series

        series.table.update_fields(self)

    def __iter__(self) -> _Iterable["Series"]:
        for db_id in TableBase.__iter__(self):
            yield Series(self, db_id)

    def __getitem__(self, item) -> "Series":
        if isinstance(item, int):
            if item in self:
                return Series(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Series(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, mfg_id: int, description: str, ) -> "Series":
        db_id = TableBase.insert(self, name=name, mfg_id=mfg_id, description=description)
        return Series(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Series(EntryBase, NameMixin, DescriptionMixin, ManufacturerMixin):
    _table: SeriesTable = None

    def build_monitor_packet(self):
        packet = {
            'series': [self.db_id]
        }

        return packet
