from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import text_ctrl as _text_ctrl

if TYPE_CHECKING:
    from ...database.global_db import cavity_lock as _cavity_lock


class AddCavityLockDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, table: "_cavity_lock.CavityLocksTable"):

        self.table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Add to Database',
                                         label='Add Cavity Lock')

        if name:
            self.name = _text_ctrl.TextCtrl(self.panel, 'Name:',
                                            (-1, -1), style=wx.TE_READONLY,
                                            apply_button=False)
            self.name.SetValue(name)

        else:
            self.name = _text_ctrl.TextCtrl(self.panel, 'Name:',
                                            (-1, -1), apply_button=False)
            self.name.SetValue('')
            self.name.Bind(wx.EVT_CHAR, self.on_name)

        table.execute('SELECT name from cavity_locks;')
        rows = table.fetchall()
        self._names = sorted(row[0] for row in rows)

        self.description = _text_ctrl.TextCtrl(self.panel, 'Description:',
                                               (-1, -1), style=wx.TE_MULTILINE,
                                               apply_button=False)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.name, 1, wx.EXPAND)
        vsizer.Add(self.description, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)

    def on_name(self, evt):
        def _do():
            value = self.name.GetValue()
            hit = any(s.startswith(value) for s in self._names)
            if hit:
                self.name.SetStyle(0, len(value),
                                   wx.TextAttr(wx.Colour(255, 0, 0)))
            else:
                self.name.SetStyle(0, len(value),
                                   wx.TextAttr(self.GetForegroundColour()))

        wx.CallAfter(_do)
        evt.Skip()

    def ShowModal(self):
        res = _dialog_base.BaseDialog.ShowModal(self)
        if res == wx.ID_OK:
            name = self.name.GetValue().strip()
            if any(s.startswith(name) for s in self._names):
                return wx.ID_CANCEL

        return res

    def GetValue(self):
        name = self.name.GetValue().strip()
        description = self.description.GetValue().strip()
        return name, description
