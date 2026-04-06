from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin
import uuid
from ... import color as _color


class ColorsTable(TableBase):
    __table_name__ = 'colors'

    def _table_needs_update(self) -> bool:
        from ..create_database import colors

        return colors.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import colors

        colors.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        colors.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import colors

        colors.table.update_fields(self)

    def __iter__(self) -> _Iterable["Color"]:
        for db_id in TableBase.__iter__(self):
            yield Color(self, db_id)

    def __getitem__(self, item) -> "Color":
        if isinstance(item, int):
            if item in self:
                return Color(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Color(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, rgb: int) -> "Color":
        db_id = TableBase.insert(self, name=name, rgb=rgb)
        return Color(self, db_id)


class Color(EntryBase, NameMixin):
    _table: ColorsTable = None
    _color_id: str = None

    def build_monitor_packet(self):
        packet = {
            'colors': [self.db_id],
        }

        return packet

    def _update_color(self, c: _color.Color) -> None:
        self._table.update(self._db_id, rgb=c.GetRGBA())

    @property
    def ui(self) -> _color.Color:
        if self._color_id is None:
            self._color_id = str(uuid.uuid4())

        color = _color.Color(*self.rgb, db_id=self._color_id)
        color.bind(self._update_color)
        return color

    @property
    def rgb(self) -> tuple[int, int, int, int]:
        rgba = self._table.select('rgb', id=self._db_id)[0][0]

        r = rgba >> 24
        g = (rgba >> 16) & 0xFF
        b = (rgba >> 8) & 0xFF
        a = rgba & 0xFF
        return r, g, b, a

    @rgb.setter
    def rgb(self, value: tuple[int, int, int, int]):
        r, g, b, a = value

        rgba = r << 24 | b << 16 | b << 8 | a

        self._table.update(self._db_id, rgb=rgba)

    @property
    def propgrid(self) -> wxpg.PGProperty:
        from ...ui.editor_obj.prop_grid import combobox_prop as _combobox_prop
        from ...ui.editor_obj.prop_grid import long_string_prop as _long_string_prop

        group_prop = wxpg.PGProperty('Family', 'family')

        rows = self.table.select('name, description', mfg_id=self.mfg_id)

        choices = [item[0] for item in rows]
        name_prop = _combobox_prop.ComboboxProperty('Name', 'name', self.name, choices)
        desc_prop = _long_string_prop.LongStringProperty('Description', 'description', self.description)

        group_prop.AppendChild(name_prop)
        group_prop.AppendChild(desc_prop)

        return group_prop
