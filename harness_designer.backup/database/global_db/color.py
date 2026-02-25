from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin
import uuid
from ...wrappers import color as _color


class ColorsTable(TableBase):
    __table_name__ = 'colors'

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
