import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import plating as _plating
from . import descriptionctrl as _descriptionctrl


class PlatingCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables, label):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.platings_table.choices

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(self, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')
        self.plating_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)
        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(self)

        symbol_sizer = utils.HSizer(self, label, self.choice_ctrl)
        desc_sizer = utils.HSizer(self, None, self.desc_ctrl)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(symbol_sizer)
        sizer.Add(desc_sizer)

        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        symbol = self.choice_ctrl.GetString(index)
        self.plating_db_obj = self.global_db.platings_table[symbol]
        self.desc_ctrl.SetValue(self.plating_db_obj.description)
        evt.Skip()

    def SetDBObject(self, db_obj: _plating.Plating) -> None:
        self.plating_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.symbol)
        self.desc_ctrl.SetValue(db_obj.description)

    def GetValue(self) -> int:
        symbol = self.choice_ctrl.GetValue()

        if self.plating_db_obj is not None and symbol == self.plating_db_obj.name:
            return self.plating_db_obj.db_id

        desc = self.desc_ctrl.GetValue()
        self.plating_db_obj = self.global_db.platings_table.insert(symbol, desc)

        self.choice_ctrl.Clear()
        self.choice_ctrl.SetItems(self.global_db.platings_table.choices)

        return self.plating_db_obj.db_id
