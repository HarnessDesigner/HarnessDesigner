import wx
from wx.lib import scrolledpanel

from ... import image as _image


class HeaderPanel(wx.Panel):

    def __init__(self, parent, label):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.bitmap = wx.Bitmap(_image.images.header_600x80.bitmap)

        font = self.GetFont()
        t_width, t_height = self.GetTextExtent(label)
        while t_width < 273 and t_height < 35:
            psize = font.GetPointSize()
            font.SetPointSize(psize + 1)
            self.SetFont(font)
            t_width, t_height = self.GetTextExtent(label)

        while t_width > 273 or t_height > 35:
            psize = font.GetPointSize()
            font.SetPointSize(psize - 1)
            self.SetFont(font)
            t_width, t_height = self.GetTextExtent(label)

        font.SetUnderlined(True)

        dc = wx.MemoryDC()
        dc.SelectObject(self.bitmap)

        gcdc = wx.GCDC(dc)
        gc = gcdc.GetGraphicsContext()

        gc.SetFont(font, wx.Colour(0, 0, 0, 255))
        gc.DrawText(label, 6.0, 6.0)

        dc.SelectObject(wx.NullBitmap)
        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

        self.sb = wx.StaticBitmap(self, wx.ID_ANY, bitmap=self.bitmap, pos=(0, 0), size=self.bitmap.GetSize())


class BaseDialog(wx.Dialog):

    def __init__(self, parent, title, label, button_ids=wx.OK | wx.CANCEL):

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title, size=(600, 800),
                           style=wx.CAPTION | wx.CLOSE_BOX | wx.STAY_ON_TOP)

        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)
        self.header = HeaderPanel(self, label)

        self.button_sizer = self.CreateSeparatedButtonSizer(button_ids)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.header, 0, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(self.panel, 0, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(self.button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        hsizer.Add(vsizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(hsizer)

    def GetValue(self):
        raise NotImplementedError
