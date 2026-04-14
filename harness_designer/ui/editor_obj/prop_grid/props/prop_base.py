import wx

from .. import events as _events


class Property(wx.Panel):

    def __init__(self, parent, label, orientation=None):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        if orientation is None:
            self._static_box = None
            self._sizer = wx.BoxSizer(wx.VERTICAL)
            self.SetSizer(self._sizer)
        else:
            self._sizer = wx.StaticBoxSizer(orientation, self, label)
            self._static_box = self._sizer.GetStaticBox()

            if orientation == wx.VERTICAL:
                sizer = wx.BoxSizer(wx.HORIZONTAL)
                sizer.Add(self._sizer, 1, wx.ALL, 5)

            else:
                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(self._sizer, 1, wx.ALL | wx.EXPAND, 5)

            self.SetSizer(sizer)

        self._label = label
        self._ctrl = None
        self._st: wx.StaticText = None
        self._button: wx.Button = None
        self._units_st: wx.StaticText = None
        self._parent = parent

    def SetToolTip(self, text):
        if self._st is not None:
            self._st.SetToolTip(text)
            self._ctrl.SetToolTip(text)
        else:
            wx.Panel.SetToolTip(self, text)

    def Realize(self):
        orientation = self._sizer.GetOrientation()

        if orientation == wx.VERTICAL:
            for child in self.GetChildren():
                child.Realize()
                self._sizer.Add(child, 0, wx.EXPAND)
        else:
            for child in self.GetChildren():
                child.Realize()
                self._sizer.Add(child, 1)

    def GetLabel(self) -> str:
        return self._label

    def SetLabel(self, value: str):
        if self._static_box is not None:
            self._static_box.SetLabel(value)
        elif self._st is not None:
            self._st.SetLabel(value)

        self._label = value

    #
    #
    # def Create(self, parent):
    #     self._parent = parent
    #
    #     if self._children:
    #         wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)
    #
    #         vsizer = wx.BoxSizer(wx.VERTICAL)
    #         hsizer = wx.BoxSizer(wx.HORIZONTAL)
    #
    #         self._expand_button = _buttons.GenButton(
    #             self, wx.ID_ANY,  self._expand_label, style=wx.BORDER_NONE, size=(15, 15))
    #
    #         self._st = wx.StaticText(self, wx.ID_ANY, label=self._label)
    #
    #         self.SetBackgroundColour(wx.Colour(215, 215, 215, 255))
    #         self._expand_button.SetBackgroundColour(wx.Colour(215, 215, 215, 255))
    #
    #         font = self._expand_button.GetFont()
    #         font.SetPointSize(font.GetPointSize() + 8)
    #         self._expand_button.SetFont(font)
    #
    #         self._expand_button.Bind(wx.EVT_BUTTON, self._on_expand_button)
    #
    #         hsizer.Add(self._expand_button, 0, wx.ALL, 5)
    #         hsizer.AddSpacer(3)
    #         hsizer.Add(self._st, 1, wx.ALL, 5)
    #         vsizer.Add(hsizer, 0, wx.EXPAND)
    #
    #         for i, child in enumerate(self._children):
    #             child_sizer = wx.BoxSizer(wx.HORIZONTAL)
    #             child_sizer.AddSpacer(27)
    #             child.Create(self)
    #             child_sizer.Add(child, 1)
    #             child_sizer.AddSpacer(27)
    #             vsizer.Add(child_sizer, 0, wx.EXPAND)
    #
    #             child.Hide()
    #
    #         self.SetSizer(vsizer)
    #
    #     else:
    #         wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
    #
    #     for args, kwargs in self._bind_event:
    #         wx.Panel.Bind(self, *args, **kwargs)

    def _send_changed_event(self, value_type, value):
        event = _events.PropertyEvent(_events.wxEVT_PROPERTY_CHANGED)
        event.SetValue(value)
        event.SetPropertyType(value_type)
        event.SetProperty(self)
        event.SetId(self.GetId())
        event.SetEventObject(self)

        self.GetEventHandler().ProcessEvent(event)
