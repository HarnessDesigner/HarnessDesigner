import wx

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import direction as _direction


class DirectionCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.directions_table.choices

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(self, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')
        self.direction_db_obj = None

        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)

        sizer = utils.HSizer(self, 'Direction:', self.choice_ctrl)
        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.direction_db_obj = self.global_db.directions_table[name]
        evt.Skip()

    def SetDBObject(self, db_obj: _direction.Direction) -> None:
        self.direction_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.name)

    def GetValue(self) -> int:
        name = self.choice_ctrl.GetValue()

        if self.direction_db_obj is not None and name == self.direction_db_obj.name:
            return self.direction_db_obj.db_id

        self.direction_db_obj = self.global_db.directions_table.insert(name)

        self.choice_ctrl.Clear()
        self.choice_ctrl.SetItems(self.global_db.directions_table.choices)

        return self.direction_db_obj.db_id
