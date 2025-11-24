import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import adhesive as _adhesive
from . import descriptionctrl as _descriptionctrl
from . import accessoryctrl as _accessoryctrl


class AdhesiveCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.adhesives_table.choices

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(self, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')
        self.adhesive_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)
        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(self)
        self.accessory_ctrl = _accessoryctrl.AccessoryCtrl(self, global_db)

        name_sizer = utils.HSizer(self, 'Adhesive:', self.choice_ctrl)
        desc_sizer = utils.HSizer(self, None, self.desc_ctrl)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(name_sizer)
        sizer.Add(desc_sizer)

        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.adhesive_db_obj = self.global_db.adhesives_table[name]
        self.desc_ctrl.SetValue(self.adhesive_db_obj.description)
        self.accessory_ctrl.SetValue(self.adhesive_db_obj.accessories)
        evt.Skip()

    def SetDBObject(self, db_obj: _adhesive.Adhesive) -> None:
        self.adhesive_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.code)
        self.desc_ctrl.SetValue(db_obj.description)
        self.accessory_ctrl.SetValue(db_obj.accessories)

    def GetValue(self) -> int:
        name = self.choice_ctrl.GetValue()

        if self.adhesive_db_obj is not None and name == self.adhesive_db_obj.name:
            return self.adhesive_db_obj.db_id

        desc = self.desc_ctrl.GetValue()

        self.adhesive_db_obj = self.global_db.adhesives_table.insert(name, desc)

        self.choice_ctrl.Clear()
        self.choice_ctrl.SetItems(self.global_db.adhesives_table.choices)

        return self.adhesive_db_obj.db_id
