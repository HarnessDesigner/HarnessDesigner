import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import color as _color


class ColorCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables, label):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.colors_table.choices

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(self, choices=choices)
        self.choice_ctrl.SetValue('Black')
        self.color_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)

        self.color_ctrl = wx.ColourPickerCtrl(self, wx.ID_ANY, colour=global_db.colors_table['Black'].ui, size=(30, -1))
        self.color_ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_colour)

        sizer = utils.HSizer(self, label, self.choice_ctrl, None, self.color_ctrl)

        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.color_db_obj = self.global_db.colors_table[name]
        self.color_ctrl.SetColour(self.color_db_obj.ui)
        evt.Skip()

    def on_colour(self, evt: wx.ColourPickerEvent):
        color = evt.GetColour()
        rgba = color.GetRGBA()
        for db_color in self.global_db.colors_table:
            if db_color.ui.GetRGBA() == rgba:
                self.choice_ctrl.SetValue(db_color.name)
                self.color_db_obj = db_color
            break
        else:
            self.color_db_obj = None

        evt.Skip()

    def SetDBObject(self, db_obj: _color.Color) -> None:
        self.color_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.name)
        self.color_ctrl.SetColour(db_obj.ui)

    def GetValue(self) -> int:
        color_name = self.choice_ctrl.GetValue()

        if self.color_db_obj is not None:
            if color_name == self.color_db_obj.name:
                return self.color_db_obj.db_id

        color = self.color_ctrl.GetColour()
        rgba = color.GetRGBA()

        self.color_db_obj = self.global_db.colors_table.insert(color_name, rgba)

        self.choice_ctrl.Clear()
        self.choice_ctrl.SetItems(self.global_db.colors_table.choices)

        return self.color_db_obj.db_id
