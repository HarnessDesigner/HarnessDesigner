from typing import Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class ProtectionsTable(TableBase):
    __table_name__ = 'protections'

    def _table_needs_update(self) -> bool:
        from ..create_database import protections

        return protections.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import protections

        protections.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        protections.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import protections

        protections.table.update_fields(self)

    def __iter__(self) -> _Iterable["Protection"]:
        for db_id in TableBase.__iter__(self):
            yield Protection(self, db_id)

    def __getitem__(self, item) -> "Protection":
        if isinstance(item, int):
            if item in self:
                return Protection(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Protection(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "Protection":
        db_id = TableBase.insert(self, name=name)
        return Protection(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Protection(EntryBase, NameMixin):
    _table: ProtectionsTable = None

    def build_monitor_packet(self):
        packet = {
            'protections': [self.db_id]
        }

        return packet

    @property
    def propgrid(self) -> _prop_grid.Property:
        rows = self.table.select('name')

        choices = [item[0] for item in rows]
        name_prop = _prop_grid.ComboBoxProperty('Protections', 'name', self.name, choices)

        return name_prop
