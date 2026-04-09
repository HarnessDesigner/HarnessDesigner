from typing import Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import DescriptionMixin


class PlatingsTable(TableBase):
    __table_name__ = 'platings'

    def _table_needs_update(self) -> bool:
        from ..create_database import platings

        return platings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import platings

        platings.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        platings.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import platings

        platings.table.update_fields(self)

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

    def build_monitor_packet(self):
        packet = {
            'platings': [self.db_id],
        }

        return packet

    @property
    def symbol(self) -> str:
        return self._table.select('symbol', id=self._db_id)[0][0]

    @symbol.setter
    def symbol(self, value: str):
        self._table.update(self._db_id, symbol=value)

    @property
    def propgrid(self) -> _prop_grid.Property:
        group_prop = _prop_grid.Property('Plating', 'plating')
        rows = self.table.select('symbol', 'description')

        choices = [item[0] for item in rows]
        name_prop = _prop_grid.ComboBoxProperty('Symbol', 'symbol', self.symbol, choices)
        desc_prop = _prop_grid.LongStringProperty('Description', 'description', self.description)

        group_prop.Append(name_prop)
        group_prop.Append(desc_prop)

        return group_prop
