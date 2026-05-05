from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from . import add_manufacturer_db as _add_manufacturer_db

from ..widgets import text_ctrl as _text_ctrl
from ..widgets import combobox_ctrl as _combobox_ctrl

if TYPE_CHECKING:
    from ...database.global_db import family as _family


class AddFamilyDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, mfg_name, table: "_family.FamiliesTable"):

        self.table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Add to Database', label='Add Family')

        if name:
            self.name = _text_ctrl.TextCtrl(self.panel, 'Name:', (-1, -1), 
                                            style=wx.TE_READONLY, apply_button=False)
            self.name.SetValue(name)
        else:
            self.name = _text_ctrl.TextCtrl(self.panel, 'Name:', 
                                            (-1, -1), apply_button=False)
            self.name.SetValue(name)
            self.name.Bind(wx.EVT_CHAR, self.on_name)

        table.execute('SELECT name from families;')
        rows = table.fetchall()
        self._names = sorted(row[0] for row in rows)

        table.execute('SELECT name from manufacturers;')
        rows = table.fetchall()
        self._mfg_names = sorted(row[0] for row in rows)
        
        if mfg_name:
            self.mfg = _text_ctrl.TextCtrl(self.panel, 'Manufacturer:', 
                                           (-1, -1), style=wx.TE_READONLY, 
                                           apply_button=False)
            self.mfg.SetValue(mfg_name)
        else:
            self.mfg = _combobox_ctrl.ComboBoxCtrl(self.panel, 'Manufacturer:', 
                                                   self._mfg_names)
            self.mfg.Bind(wx.EVT_COMBOBOX, self._on_mfg)
        
        self.description = _text_ctrl.TextCtrl(self.panel, 'Description:', 
                                               (-1, -1), style=wx.TE_MULTILINE,
                                               apply_button=False)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.name, 1, wx.EXPAND)
        vsizer.Add(self.mfg, 1, wx.EXPAND)
        vsizer.Add(self.description, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)
    
    def on_name(self, evt):
        def _do():
            value = self.name.GetValue()
            hit = any(s.startswith(value.strip()) for s in self._names)
            if hit:
                self.name.SetStyle(0, len(value), 
                                   wx.TextAttr(wx.Colour(255, 0, 0)))
            else:
                self.name.SetStyle(0, len(value), 
                                   wx.TextAttr(self.GetForegroundColour()))

        wx.CallAfter(_do)
        evt.Skip()
        
    def _on_mfg(self, evt: wx.CommandEvent):
        mfg = self.mfg.GetValue().strip()
        
        if mfg not in self._mfg_names:
            dlg = _add_manufacturer_db.AddManufacturerDialog(self, mfg,
                                                             self.table.db.manufacturers_table)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    value = dlg.GetValue()
                    try:
                        self.table.db.manufacturers_table.insert(*value)

                        self._mfg_names.append(mfg)
                        self._mfg_names = sorted(self._mfg_names)
                        self.mfg.SetItems(self._mfg_names)
                        self.mfg.SetValue(mfg)
                    except Exception as err:  # NOQA
                        from ...logger import logger as _logger

                        _logger.traceback(err, 'Adding Manufacturer')
                        return
                else:
                    return

            finally:
                dlg.Destroy()

        evt.Skip()
        
    def ShowModal(self):
        res = _dialog_base.BaseDialog.ShowModal(self)
        if res == wx.ID_OK:
            name = self.name.GetValue().strip()
            if any(s.startswith(name) for s in self._names):
                return wx.ID_CANCEL

            mfg = self.mfg.GetValue().strip()
            if mfg not in self._mfg_names:
                return wx.ID_CANCEL
            
        return res
    
    def GetValue(self):
        name = self.name.GetValue().strip()
        mfg = self.mfg.GetValue().strip()
        description = self.description.GetValue().strip()
        return name, mfg, description
