import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import material as _material
from . import descriptionctrl as _descriptionctrl


class MaterialCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.materials_table.choices

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(self, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')
        self.material_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)
        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(self)

        name_sizer = utils.HSizer(self, 'Material:', self.choice_ctrl)
        desc_sizer = utils.HSizer(self, None, self.desc_ctrl)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(name_sizer)
        sizer.Add(desc_sizer)

        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.material_db_obj = self.global_db.materials_table[name]
        self.desc_ctrl.SetValue(self.material_db_obj.description)
        evt.Skip()

    def SetDBObject(self, db_obj: _material.Material) -> None:
        self.material_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.name)
        self.desc_ctrl.SetValue(db_obj.description)

    def GetValue(self) -> int:
        name = self.choice_ctrl.GetValue()

        if self.material_db_obj is not None and name == self.material_db_obj.name:
            return self.material_db_obj.db_id

        desc = self.desc_ctrl.GetValue()

        self.material_db_obj = self.global_db.materials_table.insert(name, desc)

        self.choice_ctrl.Clear()
        self.choice_ctrl.SetItems(self.global_db.materials_table.choices)

        return self.material_db_obj.db_id
