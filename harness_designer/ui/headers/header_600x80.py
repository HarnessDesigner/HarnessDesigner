
import wx
from ... import image as _image


class Header600x80(wx.Panel):

    def __init__(self, parent, label):
        self.bitmap = wx.Bitmap(_image.images.header_1200x80.bitmap)

        wx.Panel.__init__(self, parent, wx.ID_ANY, size=(600, 80), style=wx.BORDER_SUNKEN)
        self.SetMinClientSize((600, 80))
        self.SetMinSize((600, 80))

        self.SetMaxClientSize((600, 80))
        self.SetMaxSize((600, 80))

        font = self.GetFont()
        t_width, t_height = self.GetTextExtent(label)
        while t_width < 273 and t_height < 25:
            psize = font.GetPointSize()
            font.SetPointSize(psize + 1)
            self.SetFont(font)
            t_width, t_height = self.GetTextExtent(label)

        while t_width > 273 or t_height > 25:
            psize = font.GetPointSize()
            font.SetPointSize(psize - 1)
            self.SetFont(font)
            t_width, t_height = self.GetTextExtent(label)

        font.MakeItalic()

        dc = wx.MemoryDC()
        dc.SelectObject(self.bitmap)

        gcdc = wx.GCDC(dc)
        gc = gcdc.GetGraphicsContext()

        gc.SetFont(font, wx.Colour(0, 0, 0, 255))
        gc.DrawText(label, 12.0, 6.0)

        dc.SelectObject(wx.NullBitmap)
        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

        self.sb = wx.StaticBitmap(self, wx.ID_ANY, bitmap=self.bitmap, pos=(0, 0), size=self.bitmap.GetSize())

    def DoGetBestClientSize(self):
        return wx.Size(600, 80)
