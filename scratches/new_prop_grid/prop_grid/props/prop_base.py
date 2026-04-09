import wx
from wx.lib import buttons as _buttons

from .. import events as _events


class _PropertyPanel(wx.Panel):
    def __init__(self, parent_window, parent):
        wx.Panel.__init__(self, parent_window, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.parent = parent
        self._parent_window = parent_window

    def GetFQN(self):
        return self.parent.GetFQN()


class Property(wx.BoxSizer):

    def __init__(self, label, name='', value=None, units=None):
        self._label = label
        self._name = name
        self._value = value
        self._ctrl = None
        self._units = units
        self._st: wx.StaticText = None
        self._units_st: wx.StaticText = None
        self.__parent = None
        self.__parent_window = None
        self._tooltip = None
        self._expand_button: wx.Button = None
        self._button: wx.Button = None
        self._panel: _PropertyPanel = None

        self._expand_label = chr(0x229E)
        self._collapse_label = chr(0x229F)

        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        self._children = []

    def AppendChild(self, child: "Property"):
        if not isinstance(child, Property):
            raise ValueError

        self._children.append(child)

    def GetValue(self):
        return self._value

    def SetValue(self, value):
        self._value = value

    def GetLabel(self) -> str:
        return self._label

    def SetLabel(self, value: str):
        self._label = value

    def GetName(self) -> str:
        return self._name

    def SetName(self, value: str):
        self._name = value

    def GetFQN(self) -> str:
        fqn = self._parent.GetFQN()

        if fqn:
            if self._name:
                return fqn + '.' + self._name

            return fqn

        return self._name

    @property
    def _parent_window(self):
        return self.__parent_window

    @property
    def _parent(self):
        return self.__parent

    def GetParent(self):
        return self._parent

    @_parent.setter
    def _parent(self, value):
        self.__parent = value

        while not isinstance(value, wx.Window):
            value = value.GetParent()

        self.__parent_window = value

    def Hide(self):
        if self._st is not None:
            self._st.Hide()

        if self._ctrl is not None:
            self._ctrl.Hide()

        if self._units_st is not None:
            self._units_st.Hide()

        if self._button is not None:
            self._button.Hide()

        if self._expand_button is not None:
            self._expand_button.Hide()

        if self._panel is not None:
            self._panel.Hide()

            sizer = self._panel.GetSizer()
            count = sizer.GetItemCount()
            for i in range(1, count):
                sizer.Hide(i)

        # for child in self._children:
        #     child.Hide()

        # count = self.GetItemCount()
        # for i in range(count):
        #     wx.BoxSizer.Hide(self, i)

        self.Layout()
        self._parent.Layout()
        self.__parent_window.Layout()
        self.__parent_window.SendSizeEvent()

    def Show(self):
        if self._st is not None:
            self._st.Show()

        if self._ctrl is not None:
            self._ctrl.Show()

        if self._units_st is not None:
            self._units_st.Show()

        if self._button is not None:
            self._button.Show()

        if self._expand_button is not None:
            self._expand_button.Show()

        if self._panel is not None:
            self._panel.Show()

            sizer = self._panel.GetSizer()
            count = sizer.GetItemCount()
            for i in range(1, count):
                sizer.Show(i)

            sizer.Layout()
            self._panel.Layout()

        # for child in self._children:
        #     child.Show()

        self.Layout()
        self._parent.Layout()
        self.__parent_window.Layout()
        self.__parent_window.SendSizeEvent()

    def Create(self, parent):
        self._parent = parent
        parent = self._parent_window

        if self._children:
            panel = self._panel = _PropertyPanel(parent, self._parent)
            panel.SetBackgroundColour(wx.Colour(215, 215, 215, 255))

            vsizer = wx.BoxSizer(wx.VERTICAL)
            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            self._st = wx.StaticText(panel, wx.ID_ANY, label=self._label)

            self._expand_button = _buttons.GenButton(
                panel, wx.ID_ANY,  self._expand_label, style=wx.BORDER_NONE, size=(15, 15))

            self._expand_button.SetBackgroundColour(wx.Colour(215, 215, 215, 255))

            font = self._expand_button.GetFont()
            font.SetPointSize(font.GetPointSize() + 8)
            self._expand_button.SetFont(font)

            self._expand_button.Bind(wx.EVT_BUTTON, self._on_expand_button)
            hsizer.Add(self._expand_button, 0, wx.ALL, 5)
            hsizer.AddSpacer(3)
            hsizer.Add(self._st, 1, wx.ALL, 5)
            vsizer.Add(hsizer, 0, wx.EXPAND)

            for child in self._children:
                child.AddSpacer(27)
                child.Create(panel)
                vsizer.Add(child, 1, wx.EXPAND)
                child.Hide()

            panel.SetSizer(vsizer)
            self.Add(panel, 1)

    def _on_expand_button(self, _):
        label = self._expand_button.GetLabel()
        if label == self._expand_label:
            self._expand_button.SetLabel(self._collapse_label)
            for child in self._children:
                child.Show()

        else:
            self._expand_button.SetLabel(self._expand_label)
            for child in self._children:
                child.Hide()

        self._panel.Layout()
        self.Layout()
        self._parent_window.SendSizeEvent()

    def _send_changed_event(self, value_type):
        event = _events.PropertyEvent(_events.wxEVT_PROPERTY_CHANGED)
        event.SetValue(self._value)
        event.SetPropertyType(value_type)
        event.SetProperty(self)
        event.SetName(self.GetFQN())
        event.SetId(self._parent_window.GetId())
        event.SetEventObject(self._parent_window)

        self._parent_window.GetEventHandler().ProcessEvent(event)

    def SetToolTip(self, text):
        self._tooltip = text

        if self._ctrl is not None:
            self._ctrl.SetToolTip(text)
