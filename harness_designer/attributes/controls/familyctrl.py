import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import family as _family
from . import descriptionctrl as _descriptionctrl
from . import manufacturerctrl as _manufacturerctrl


class FamilyCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.families_table.choices

        sb_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, 'Series')
        sb = sb_sizer.GetStaticBox()

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(sb, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')

        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(sb)
        self.mfg_ctrl = _manufacturerctrl.ManufacturerCtrl(sb, global_db)

        self.family_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)

        choice_sizer = utils.HSizer(sb, 'Name:', self.choice_ctrl)
        desc_sizer = utils.HSizer(sb, None, self.desc_ctrl)
        mfg_sizer = utils.HSizer(sb, None, self.mfg_ctrl)

        sb_sizer.Add(choice_sizer)
        sb_sizer.Add(desc_sizer)
        sb_sizer.Add(mfg_sizer)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sb_sizer)

        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.family_db_obj = self.global_db.families_table[name]
        self.mfg_ctrl.SetDBObject(self.family_db_obj.manufacturer)
        self.desc_ctrl.SetValue(self.family_db_obj.description)
        evt.Skip()

    def SetDBObject(self, db_obj: _family.Family) -> None:
        self.family_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.name)
        self.mfg_ctrl.SetDBObject(self.family_db_obj.manufacturer)
        self.desc_ctrl.SetValue(self.family_db_obj.description)

    def GetValue(self) -> int:
        name = self.choice_ctrl.GetValue()

        try:
            return self.global_db.families_table[name].db_id
        except KeyError:
            return self.global_db.families_table.insert(name, self.mfg_ctrl.GetValue(), self.desc_ctrl.GetValue()).db_id
