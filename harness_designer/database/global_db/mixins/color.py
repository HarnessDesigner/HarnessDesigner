from typing import TYPE_CHECKING

import wx

from ....ui.editor_obj import prop_grid as _prop_grid

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


class ColorControl(_prop_grid.ColorProperty):

    def __init__(self, parent):
        self.choices: list[list[str, int]] = None
        self.db_obj: ColorMixin = None

        super().__init__(parent, 'Color', ['None', wx.BLACK], [])

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_color)

    def set_obj(self, db_obj: ColorMixin):
        self.db_obj = db_obj
        color = db_obj.color

        db_obj.table.execute('SELECT name, rgb from colors;')
        rows = db_obj.table.fetchall()
        self.choices = [list(row) for row in rows]

        self.SetItems(self.choices)
        self.SetValue([color.name, color.ui])

    def _on_color(self, evt):
        name, color = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id, rgba FROM colors WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        r = color.GetRed()
        g = color.GetGreen()
        b = color.GetBlue()
        a = color.GetAlpha()

        rgba = r << 24 | g << 16 | b << 8 | a

        if rows:
            db_id, stored_rgba = rows[0]

            if rgba != stored_rgba:
                self.db_obj.color_id = db_id
                self.db_obj.color.rgb = rgba
        else:
            db_obj = self.db_obj.table.db.colors_table.insert(name, rgba)
            db_id = db_obj.db_id

            self.choices.append([name, color])
            self.SetItems(self.choices)
            self.SetValue([name, color])

        self.db_obj.color_id = db_id
