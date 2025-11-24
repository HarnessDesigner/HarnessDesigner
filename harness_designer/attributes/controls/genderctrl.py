import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import gender as _gender


class GenderCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.genders_table.choices

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(self, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')
        self.gender_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)

        sizer = utils.HSizer(self, 'Gender:', self.choice_ctrl)
        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.gender_db_obj = self.global_db.genders_table[name]
        evt.Skip()

    def SetDBObject(self, db_obj: _gender.Gender) -> None:
        self.gender_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.name)

    def GetValue(self) -> int:
        name = self.choice_ctrl.GetValue()

        if self.gender_db_obj is not None and name == self.gender_db_obj.name:
            return self.gender_db_obj.db_id

        self.gender_db_obj = self.global_db.genders_table.insert(name)

        self.choice_ctrl.Clear()
        self.choice_ctrl.SetItems(self.global_db.genders_table.choices)

        return self.gender_db_obj.db_id
