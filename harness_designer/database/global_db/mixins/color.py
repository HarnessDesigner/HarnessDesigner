from typing import TYPE_CHECKING

from wx import propgrid as wxpg

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import color as _color


class ColorMixin(BaseMixin):

    @property
    def color(self) -> "_color.Color":
        color_id = self._table.select('color_id', id=self._db_id)
        color = self._table.db.colors_table[color_id[0][0]]
        return color

    @color.setter
    def color(self, value: "_color.Color") -> None:
        self.color_id = value.db_id

    @property
    def color_id(self) -> int:
        return self._table.select('color_id', id=self._db_id)[0][0]

    @color_id.setter
    def color_id(self, value: int):
        self._table.update(self._db_id, color_id=value)

    @property
    def _color_propgrid(self) -> wxpg.PGProperty:
        prop = self.color.propgrid
        return prop
