import wx.lib.scrolledpanel as scrolled
import wx


class SearchList(scrolled.ScrolledPanel):

    def __init__(self, parent, direction, *items):
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        sizer = wx.BoxSizer(direction)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        for item in items:
            if isinstance(item, (list, tuple)):
                line_sizer = wx.BoxSizer(wx.HORIZONTAL)

                for subitem in item:
                    if isinstance(subitem, str):
                        st = wx.StaticText(self, wx.ID_ANY, label=subitem)
                        line_sizer.Add(st, 0, wx.ALL, 2)
                    else:
                        subitem.Reparent(self)
                        line_sizer.Add(subitem, 0, wx.ALL, 2)

                sizer.Add(line_sizer, 0)
            elif isinstance(item, str):
                st = wx.StaticText(self, wx.ID_ANY, label=item)
                vsizer.Add(st, 0, wx.ALIGN_CENTER | wx.ALL, 5)
            else:
                item.Reparent(self)
                if len(vsizer.GetChildren()) == 1:
                    vsizer.Add(item, 0, wx.ALIGN_CENTER)
                    sizer.Add(vsizer, 0)
                    vsizer = wx.BoxSizer(wx.VERTICAL)
                else:
                    sizer.Add(item, 0)

        self.SetSizer(sizer)
        self.SetupScrolling()


class SearchPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.phrase_ctrl = wx.TextCtrl(self, wx.ID_ANY, value="", size=(150, -1))
        self.go_button = wx.Button(self, wx.ID_ANY, label='Go')




class PartSelector(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        wx.TreeCtrl(self, wx.ID_ANY, )

