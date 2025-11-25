# WireAttrPanel
# TransAttrPanel
# TerminalAttrPanel
# SpliceAttrPanel
# HousingAttrPanel
# ConnectorAttrPanel
# BundleAttrPanel
# CavityAttrPanel
# MfgAttrPanel
# BootAttrPanel
# CoverAttrPanel
# CPALockAttrPanel
# TPALockAttrPanel
# SealAttrPanel

import wx

from ..widgets import foldpanelbar as _foldpanelbar

from ..database import global_db as _global_db


class AttributePanel(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables, first_color, second_color, text_colour):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.global_db = global_db

        self.fpb = _foldpanelbar.FoldPanelBar(self)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.fpb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 0, wx.EXPAND)

        style = _foldpanelbar.CaptionBarStyle()
        style.SetCaptionStyle(_foldpanelbar.CAPTIONBAR_GRADIENT_H)
        style.SetFirstColour(wx.Colour(*first_color))
        style.SetSecondColour(wx.Colour(*second_color))
        style.SetCaptionColour(wx.Colour(*text_colour))
        self.fpb.ApplyCaptionStyleAll(style)

        self.db_obj = None
        self.save_button = wx.Button(self, wx.ID_ANY, label='Save', size=(40, -1))
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.AddStretchSpacer(1)
        h_sizer.Add(self.save_button, wx.ALL, 5)

        vsizer.Add(h_sizer)

        self.SetSizer(vsizer)

    def on_save(self, evt):
        evt.Skip()

    def DeleteBars(self):
        for i in range(self.fpb.GetCount()):
            panel = self.fpb.GetFoldPanel(i)
            self.fpb.DeleteFoldPanel(panel)

    def AppendBar(self, label: str) -> _foldpanelbar.FoldPanelItem:
        return self.fpb.AddFoldPanel(label, True)
