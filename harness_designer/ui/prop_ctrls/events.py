import wx

wxEVT_PROPERTY_CHANGED = wx.NewEventType()
EVT_PROPERTY_CHANGED = wx.PyEventBinder(wxEVT_PROPERTY_CHANGED, 0)


class PropertyEvent(wx.CommandEvent):

    def __init__(self, evtType):
        wx.CommandEvent.__init__(self, evtType)
        self._name = None
        self._property = None
        self._property_type = None
        self._value = None

    def GetName(self) -> str:
        return self._name

    def SetName(self, value: str):
        self._name = value

    def SetProperty(self, value):
        self._property = value

    def Getproperty(self):
        return self._property

    def SetPropertyType(self, value):
        self._property_type = value

    def GetPropertyType(self):
        return self._property_type

    def GetValue(self):
        return self._value

    def SetValue(self, value):
        self._value = value
