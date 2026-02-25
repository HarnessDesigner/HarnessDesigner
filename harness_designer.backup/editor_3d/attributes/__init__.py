import wx
from wx.lib import scrolledpanel


class AttributePanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY)

        self.SetupScrolling(False, True)

        self._data = None

    def SetData(self, data):
        self._data = data
