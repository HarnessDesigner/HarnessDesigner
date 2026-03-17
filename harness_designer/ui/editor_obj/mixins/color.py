
from typing import TYPE_CHECKING

import wx

from ...widgets import color_ctrl as _color_ctrl

if TYPE_CHECKING:
    from ....database.global_db.mixins import color as _color


class ColorMixin:

    def __init__(self, panel, label, db_obj: "_color.ColorMixin", callback):

        ctrl = _color_ctrl.ColorCtrl(panel, label, db_obj.table)
        sizer = panel.GetSizer()
        sizer.Add(ctrl, 1, wx.EXPAND)

        def _on_color(evt: wx.ColourPickerEvent):

            color = evt.GetColour()
            name = ctrl.GetValue()

            r = color.GetRed()
            g = color.GetGreen()
            b = color.GetBlue()

            rgba = r << 24 | g << 16 | b << 8 | 0xFF

            db_obj.table.execute('SELECT id FROM colors WHERE name="{name}" AND rgb={rgba};')
            rows = db_obj.table.fetchall()
            if rows:
                color_id = rows[0][0]
            else:
                db_obj.table.execute('INSERT INTO colors (name, rgb) VALUES (?, ?);', (name, rgba))
                db_obj.table.commit()
                color_id = db_obj.table.lastrowid

            callback(color_id)

            evt.Skip()

        ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, _on_color)
