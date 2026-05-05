import wx


class PropertyGrid(wx.Notebook):

    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_FIXEDWIDTH)

    def Clear(self):
        self.DeleteAllPages()

    def Append(self, item):
        item.Realize()
        self.AddPage(item, item.GetName())

