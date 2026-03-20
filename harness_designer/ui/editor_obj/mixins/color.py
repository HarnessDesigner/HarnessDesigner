
from typing import TYPE_CHECKING

import wx

from ...widgets import color_ctrl as _color_ctrl

if TYPE_CHECKING:
    from ....database.global_db import color as _colortable
    from .... import color as _color


class ColorMixin:

    def __init__(self, panel, label, table: "_colortable.ColorsTable",  color: _color.Color, callback):

        ctrl = _color_ctrl.ColorCtrl(panel, label, table)
        ctrl.SetValue(color)

        sizer = panel.GetSizer()
        sizer.Add(ctrl, 1, wx.EXPAND)

        def _on_color(evt: wx.ColourPickerEvent):
            c = evt.GetColour()
            name = ctrl.GetValue()

            r = c.GetRed()
            g = c.GetGreen()
            b = c.GetBlue()

            rgba = r << 24 | g << 16 | b << 8 | 0xFF

            table.execute('SELECT id FROM colors WHERE name="{name}" AND rgb={rgba};')
            rows = table.fetchall()
            if rows:
                color_id = rows[0][0]
            else:
                c_obj = table.insert(name, rgba)
                color_id = c_obj.db_id

            callback(color_id)

            evt.Skip()

        ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, _on_color)
