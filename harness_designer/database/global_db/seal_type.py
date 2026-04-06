from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class SealTypesTable(TableBase):
    __table_name__: str = 'seal_types'

    def _table_needs_update(self) -> bool:
        from ..create_database import seal_types

        return seal_types.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import seal_types

        seal_types.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        seal_types.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import seal_types

        seal_types.table.update_fields(self)

    def __iter__(self) -> _Iterable["SealType"]:
        for db_id in TableBase.__iter__(self):
            yield SealType(self, db_id)

    def __getitem__(self, item) -> "SealType":
        if isinstance(item, int):
            if item in self:
                return SealType(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return SealType(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str) -> "SealType":

        db_id = TableBase.insert(self, name=name)
        return SealType(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class SealType(EntryBase, NameMixin):
    _table: SealTypesTable = None

    def build_monitor_packet(self):
        packet = {
            'seal_types': [self.db_id]
        }

        return packet

    @property
    def propgrid(self) -> wxpg.PGProperty:
        from ...ui.editor_obj.prop_grid import combobox_prop as _combobox_prop

        rows = self.table.select('name')

        choices = [item[0] for item in rows]
        name_prop = _combobox_prop.ComboboxProperty('Seal Type', 'name', self.name, choices)

        return name_prop
