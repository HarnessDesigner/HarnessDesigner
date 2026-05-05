import wx

from . import events as _events


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
                sizer.Add(self._sizer, 0, wx.ALL | wx.EXPAND, 5)

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
        if self._static_box is not None:
            orientation = self._sizer.GetOrientation()

            if orientation == wx.VERTICAL:
                for child in self.GetChildren():
                    if child == self._static_box:
                        continue

                    child.Reparent(self._static_box)
                    child.Realize()
                    self._sizer.Add(child, 0, wx.EXPAND)
            else:
                for child in self.GetChildren():
                    if child == self._static_box:
                        continue

                    child.Reparent(self._static_box)
                    child.Realize()
                    self._sizer.Add(child, 1)
        else:
            for child in self.GetChildren():
                child.Realize()
                self._sizer.Add(child, 0, wx.EXPAND)

        self.Layout()
        self.Refresh(False)

    def GetLabel(self) -> str:
        return self._label

    def SetLabel(self, value: str):
        if self._static_box is not None:
            self._static_box.SetLabel(value)
        elif self._st is not None:
            self._st.SetLabel(value)

        self._label = value

    def Enable(self, flag=True):
        for child in self.GetChildren():
            child.Enable(flag)

    def _send_changed_event(self, value_type, value):
        event = _events.PropertyEvent(_events.wxEVT_PROPERTY_CHANGED)
        event.SetValue(value)
        event.SetPropertyType(value_type)
        event.SetProperty(self)
        event.SetId(self.GetId())
        event.SetEventObject(self)

        self.GetEventHandler().ProcessEvent(event)
