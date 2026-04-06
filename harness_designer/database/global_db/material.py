
from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class MaterialsTable(TableBase):
    __table_name__ = 'materials'

    def _table_needs_update(self) -> bool:
        from ..create_database import materials

        return materials.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import materials

        materials.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        materials.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import materials

        materials.table.update_fields(self)

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

    def build_monitor_packet(self):
        packet = {
            'materials': [self.db_id],
        }

        return packet

    @property
    def propgrid(self) -> wxpg.PGProperty:
        from ...ui.editor_obj.prop_grid import combobox_prop as _combobox_prop
        from ...ui.editor_obj.prop_grid import long_string_prop as _long_string_prop

        group_prop = wxpg.PGProperty('Material', 'material')

        rows = self.table.select('name', 'description')

        choices = [item[0] for item in rows]
        name_prop = _combobox_prop.ComboboxProperty('Name', 'name', self.name, choices)
        desc_prop = _long_string_prop.LongStringProperty('Description', 'description', self.description)

        group_prop.AppendChild(name_prop)
        group_prop.AppendChild(desc_prop)

        return group_prop
