import wx
from wx.lib import scrolledpanel


class Category(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, name):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self._name = name
        self._children = []

        self._sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self._sizer)

    def Realize(self):
        for child in self.GetChildren():
            child.Realize()
            self._sizer.Add(child, 0, wx.EXPAND)

    def GetName(self):
        return self._name


class PropertyGrid(wx.Notebook):

    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_FIXEDWIDTH)

    def Clear(self):
        self.DeleteAllPages()

    def Append(self, item):
        item.Realize()
        self.AddPage(item, item.GetName())

