from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin, ManufacturerMixin


class FamiliesTable(TableBase):
    __table_name__ = 'families'

    def _table_needs_update(self) -> bool:
        from ..create_database import families

        return families.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import families

        families.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        families.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import families

        families.table.update_fields(self)

    def __iter__(self) -> _Iterable["Family"]:
        for db_id in TableBase.__iter__(self):
            yield Family(self, db_id)

    def __getitem__(self, item) -> "Family":
        if isinstance(item, int):
            if item in self:
                return Family(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Family(self, db_id[0][0])

        raise KeyError(item)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str, mfg_id: int, description: str) -> "Family":
        db_id = TableBase.insert(self, name=name, mfg_id=mfg_id, description=description)
        return Family(self, db_id)


class Family(EntryBase, NameMixin, DescriptionMixin, ManufacturerMixin):
    _table: FamiliesTable = None

    def build_monitor_packet(self):
        packet = {
            'families': [self.db_id],
        }

        return packet

    @property
    def propgrid(self) -> wxpg.PGProperty:
        from ...ui.editor_obj.prop_grid import combobox_prop as _combobox_prop
        from ...ui.editor_obj.prop_grid import long_string_prop as _long_string_prop

        group_prop = wxpg.PGProperty('Family', 'family')

        rows = self.table.select('name', 'description', mfg_id=self.mfg_id)

        choices = [item[0] for item in rows]
        name_prop = _combobox_prop.ComboboxProperty('Name', 'name', self.name, choices)
        desc_prop = _long_string_prop.LongStringProperty('Description', 'description', self.description)

        group_prop.AppendChild(name_prop)
        group_prop.AppendChild(desc_prop)

        return group_prop
