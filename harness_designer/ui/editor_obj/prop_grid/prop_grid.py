import wx
from wx.lib import scrolledpanel


class Category(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, label):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self._label = label
        self._sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self._sizer)

    def Realize(self):
        for child in self.GetChildren():
            try:
                child.Realize()
            except AttributeError:
                pass

            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            if isinstance(child, wx.Notebook):
                hsizer.Add(child, 1, wx.EXPAND)
                self._sizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 10)
            else:
                hsizer.Add(child, 1)
                self._sizer.Add(hsizer, 0, wx.EXPAND)

        self.Layout()
        self.SetupScrolling()
        self.Refresh(False)

    def GetLabel(self):
        return self._label

    def SetLabel(self, value):
        self._label = value


class PropertyGrid(wx.Notebook):

    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_FIXEDWIDTH)

    def Clear(self):
        self.DeleteAllPages()

    def Append(self, item):
        item.Realize()
        self.AddPage(item, item.GetName())

