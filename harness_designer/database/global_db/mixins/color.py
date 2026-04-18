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

    @property
    def color_id(self) -> int:
        return self._table.select('color_id', id=self._db_id)[0][0]

    @color_id.setter
    def color_id(self, value: int):
        self._table.update(self._db_id, color_id=value)
        self._populate('color_id')


class ColorControl(_prop_grid.ColorProperty):

    def __init__(self, parent):
        self.choices: list[list[str, int]] = None
        self.db_obj: ColorMixin = None
        self.attribute_name = 'color'

        super().__init__(parent, 'Color', ['None', wx.BLACK], [])

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_color)

    def SetAttributeName(self, name):
        self.attribute_name = name

    def set_obj(self, db_obj: ColorMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.SetItems(self.choices)
            self.SetValue(['', wx.BLACK])
            self.Enable(False)
        else:
            color = getattr(db_obj, self.attribute_name)

            db_obj.table.execute('SELECT name, rgb from colors;')
            rows = db_obj.table.fetchall()
            self.choices = [list(row) for row in rows]

            self.SetItems(self.choices)
            self.SetValue([color.name, color.ui])
            self.Enable(True)

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
                setattr(self.db_obj, self.attribute_name + '_id', db_id)
                getattr(self.db_obj, self.attribute_name).rgb = rgba
        else:
            db_obj = self.db_obj.table.db.colors_table.insert(name, rgba)
            db_id = db_obj.db_id

            self.choices.append([name, color])
            self.SetItems(self.choices)
            self.SetValue([name, color])

        setattr(self.db_obj, self.attribute_name + '_id', db_id)
