from typing import TYPE_CHECKING

from .base import BaseMixin

import wx

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


class ColorControl(wx.BoxSizer):

    def __init__(self, parent, db_obj: ColorMixin):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        label = wx.StaticText(parent, wx.ID_ANY, label='Part Number:')
        ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=db_obj.color)
        ctrl.Enable(False)
        self.Add(label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        self.Add(ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

    def Save(self):
        pass

