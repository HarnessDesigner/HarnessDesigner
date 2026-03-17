from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import text_ctrl as _text_ctrl

if TYPE_CHECKING:
    from ...database.global_db import plating as _plating


class AddPlatingDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, symbol, table: "_plating.PlatingsTable"):

        self.table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Add to Database', 
                                         label='Add Plating')

        if symbol:
            self.symbol = _text_ctrl.TextCtrl(self.panel, 'Symbol:',
                                            (-1, -1), style=wx.TE_READONLY, 
                                            apply_button=False)
            self.symbol.SetValue(symbol)
            
        else:
            self.symbol = _text_ctrl.TextCtrl(self.panel, 'Symbol:',
                                            (-1, -1), apply_button=False)
            self.symbol.SetValue('')
            self.symbol.Bind(wx.EVT_CHAR, self.on_symbol)

        table.execute('SELECT symbol from platings;')
        rows = table.fetchall()
        self._symbols = sorted(row[0] for row in rows)

        self.description = _text_ctrl.TextCtrl(self.panel, 'Description:', 
                                               (-1, -1), style=wx.TE_MULTILINE, 
                                               apply_button=False)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.name, 1, wx.EXPAND)
        vsizer.Add(self.description, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)
        
    def on_symbol(self, evt):
        def _do():
            value = self.symbol.GetValue()
            hit = any(s.startswith(value) for s in self._symbols)
            if hit:
                self.symbol.SetStyle(0, len(value),
                                     wx.TextAttr(wx.Colour(255, 0, 0)))
            else:
                self.symbol.SetStyle(0, len(value),
                                     wx.TextAttr(self.GetForegroundColour()))

        wx.CallAfter(_do)
        evt.Skip()
        
    def ShowModal(self):
        res = _dialog_base.BaseDialog.ShowModal(self)
        if res == wx.ID_OK:
            symbol = self.symbol.GetValue().strip()
            if any(s.startswith(symbol) for s in self._symbols):
                return wx.ID_CANCEL
            
        return res
    
    def GetValue(self):
        symbol = self.symbol.GetValue().strip()
        description = self.description.GetValue().strip()
        return symbol, description
