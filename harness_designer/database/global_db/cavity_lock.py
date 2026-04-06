
from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class CavityLocksTable(TableBase):
    __table_name__ = 'cavity_locks'

    def _table_needs_update(self) -> bool:
        from ..create_database import cavity_locks

        return cavity_locks.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import cavity_locks

        cavity_locks.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        cavity_locks.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import cavity_locks

        cavity_locks.table.update_fields(self)

    def __iter__(self) -> _Iterable["CavityLock"]:
        for db_id in TableBase.__iter__(self):
            yield CavityLock(self, db_id)

    def __getitem__(self, item) -> "CavityLock":
        if isinstance(item, int):
            if item in self:
                return CavityLock(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return CavityLock(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, description: str) -> "CavityLock":
        db_id = TableBase.insert(self, name=name, description=description)
        return CavityLock(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class CavityLock(EntryBase, NameMixin, DescriptionMixin):
    _table: CavityLocksTable = None

    def build_monitor_packet(self):
        packet = {
            'cavity_locks': [self.db_id]
        }

        return packet

    @property
    def propgrid(self) -> wxpg.PGProperty:
        from ...ui.editor_obj.prop_grid import combobox_prop as _combobox_prop
        from ...ui.editor_obj.prop_grid import long_string_prop as _long_string_prop

        group_prop = wxpg.PGProperty('Cavity Lock', 'cavity_lock')

        rows = self.table.select('name', 'description')

        choices = [item[0] for item in rows]
        name_prop = _combobox_prop.ComboboxProperty('Name', 'name', self.name, choices)
        desc_prop = _long_string_prop.LongStringProperty('Description', 'description', self.description)

        group_prop.AppendChild(name_prop)
        group_prop.AppendChild(desc_prop)

        return group_prop

