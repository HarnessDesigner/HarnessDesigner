import wx
from . import header as _header


class BaseDialog(wx.Dialog):

    def __init__(self, parent, title, size=(-1, -1), style=wx.STAY_ON_TOP, button_ids=wx.OK | wx.CANCEL):

        width, height = size
        if width == -1 and height == -1:
            style |= wx.RESIZE_BORDER

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='', size=size,
                           style=style)

        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)
        self.header = _header.Header(self, title)

        button_sizer = self.CreateStdDialogButtonSizer(button_ids)
        self.button_sizer = self.CreateSeparatedSizer(button_sizer)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.AddSpacer(10)
        vsizer.Add(self.header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        vsizer.Add(self.panel, 1, wx.ALL | wx.EXPAND, 5)
        vsizer.Add(self.button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        vsizer.AddSpacer(10)

        self.SetSizer(vsizer)
        self.CenterOnParent()

    def GetValue(self):
        raise NotImplementedError
