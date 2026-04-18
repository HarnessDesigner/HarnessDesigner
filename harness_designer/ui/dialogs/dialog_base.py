import wx
from wx.lib import scrolledpanel

from ... import image as _image
from .. import headers as _headers


class BaseDialog(wx.Dialog):

    def __init__(self, parent, title, label, size=wx.DefaultSize, button_ids=wx.OK | wx.CANCEL):

        style = wx.CAPTION | wx.CLOSE_BOX | wx.STAY_ON_TOP

        width, height = size
        if width == -1 and height == -1:
            style |= wx.RESIZE_BORDER

        if width != 600:
            width = 600

        size = (width, height)

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='', size=size,
                           style=style)

        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)
        self.header = _headers.Header600x80(self, label)

        button_sizer = self.CreateStdDialogButtonSizer(button_ids)
        self.button_sizer = self.CreateSeparatedSizer(button_sizer)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.header, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        vsizer.Add(self.panel, 1, wx.ALL | wx.EXPAND, 5)

        vsizer.Add(self.button_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        self.SetSizer(vsizer)
        self.CenterOnParent()

    def GetValue(self):
        raise NotImplementedError
