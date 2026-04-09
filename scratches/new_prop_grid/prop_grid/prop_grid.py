import wx
from wx.lib import scrolledpanel


class Category:

    def __init__(self, name):
        self._name = name

        self._children = []

    def GetName(self):
        return self._name

    def Append(self, child):
        self._children.append(child)

    def Create(self, parent):
        for child in self._children:
            child.Create(parent)
            yield child


class Grid(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, category):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.category = category

        sizer = wx.BoxSizer(wx.VERTICAL)

        for child in category.Create(self):
            sizer.Add(child, 0, wx.EXPAND)

        self._sizer = sizer

        self.SetSizer(sizer)
        self.SetupScrolling()

    def Append(self, item):
        item.Create(self)
        self._sizer.Add(item, 0, wx.EXPAND)
        self.category.append(item)
        self.SetupScrolling()

    def GetFQN(self):
        return ''


class PropertyGrid(wx.Notebook):

    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_FIXEDWIDTH)
        self._cur_category = None

        'DeleteAllPages'

    def Append(self, item):
        if isinstance(item, Category):
            self._cur_category = Grid(self, item)
            self.AddPage(self._cur_category, item.GetName())
            return

        elif self._cur_category is None:
            category = Category('General')
            self._cur_category = Grid(self, category)

        self._cur_category.Append(item)
