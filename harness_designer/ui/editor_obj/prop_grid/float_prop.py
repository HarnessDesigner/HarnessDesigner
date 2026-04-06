import wx
from wx import propgrid as wxpg

from ....geometry.decimal import Decimal as _d
from .... import utils as _utils


class FloatSpin(wx.Panel):

    def __init__(self, parent, value, min_val, max_val, inc, pos, size):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE,
                          pos=pos, size=size)

        self.__min_val = min_val
        self.__max_val = max_val
        self.__increment = inc

        precision = 0
        inc = _d(self.__increment)

        while inc < 1:
            precision += 1
            inc *= _d(10.0)

        self.__precision = precision

        w, h = pos

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.__spinctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(value),
                                            min=min_val, max=max_val,
                                            inc=self.__increment, initial=value)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.__spinctrl, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 5)

        s_inc = _d(10) * _d(self.__precision)
        slider_max = _d(100) * s_inc

        self.__s_max = int(slider_max)

        slider_value = _utils.remap(
            value, self.__min_val, self.__max_val, 0, self.__s_max)

        self.__sliderctrl = wx.Slider(self, wx.ID_ANY, value=int(slider_value),
                                      minValue=0, maxValue=int(slider_max),
                                      style=wx.SL_HORIZONTAL, pos=(0, int(h / 2)),
                                      size=(w, int(h / 2)))

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.__sliderctrl, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 5)

        self.__sliderctrl.Bind(wx.EVT_SLIDER, self._on_slider_scroll)
        self.__spinctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_spin_changed)

        self.SetSizer(vsizer)

        wx.CallAfter(self.SendSizeEvent)

    def SetSize(self, size):
        wx.Panel.SetSize(size)
        self.Refresh(False)

    def _on_slider_scroll(self, evt):

        slider_value = self.__sliderctrl.GetValue()
        spin_value = _utils.remap(
            slider_value, 0, self.__s_max, self.__min_val, self.__max_val)

        inc = _d(self.__increment)
        remaining = spin_value % inc

        if remaining:
            spin_value += inc - remaining

        self.__spinctrl.SetValue(float(spin_value))

        event = wx.SpinDoubleEvent(wx.wxEVT_SPINCTRLDOUBLE)
        event.SetValue(float(spin_value))
        event.SetEventObject(self.__spinctrl)
        event.SetId(self.__spinctrl.GetId())
        self.__spinctrl.GetEventHandler().ProcessEvent(event)

    def _on_spin_changed(self, evt: wx.SpinDoubleEvent):
        spin_value = self.__spinctrl.GetValue()

        slider_value = _utils.remap(
            spin_value, self.__min_val, self.__max_val, 0, self.__s_max)

        self.__sliderctrl.SetValue(int(slider_value))

        evt.Skip()

    def GetValue(self):
        return self.__spinctrl.GetValue()


class FloatSpinEditor(wxpg.PGEditor):

    def __init__(self):
        wxpg.PGEditor.__init__(self)

    def GetName(self):
        return 'FloatSpin'

    def CreateControls(self, propgrid, prop, pos, sz):
        w, h = sz
        h = 64 + 6

        value = float(prop.GetDisplayedString())
        min_val = prop.GetMinValue()
        max_val = prop.GetMaxValue()
        inc = prop.GetIncrement()

        ctrl = FloatSpin(propgrid.GetPanel(), value, min_val, max_val,
                         inc, pos, (w, h))

        return wxpg.PGWindowList(ctrl)

    def UpdateControl(self, prop, ctrl):
        ctrl.SetValue(float(prop.GetDisplayedString()))

    def DrawValue(self, dc, rect, prop, text):
        dc.DrawText(prop.GetDisplayedString(), rect.x + 5, rect.y)

    def OnEvent(self, propgrid, prop, ctrl, event):
        if not ctrl:
            return False

        evtType = event.GetEventType()

        if evtType == wx.wxEVT_COMMAND_TEXT_ENTER:
            if propgrid.IsEditorsValueModified():
                return True

        elif evtType == wx.wxEVT_COMMAND_TEXT_UPDATED:
            #
            # Pass this event outside wxPropertyGrid so that,
            # if necessary, program can tell when user is editing
            # a textctrl.
            event.Skip()
            event.SetId(propgrid.GetId())

            propgrid.EditorsValueWasModified()
            return False

        return False

    def GetValueFromControl(self, prop, ctrl):
        """ Return tuple (wasSuccess, newValue), where wasSuccess is True if
            different value was acquired successfully.
        """
        value = ctrl.GetValue()

        return True, value

    def SetControlStringValue(self, prop, ctrl, text):
        ctrl.SetValue(float(text))

    def OnFocus(self, prop, ctrl):
        pass

#
# floatproperty
# wxpg.PG_ATTR_MAX
# wxpg.PG_ATTR_MIN
# wxpg.PG_ATTR_SPINCTRL_STEP
# wxpg.PG_FLOAT_PRECISION
# wxpg.PG_ATTR_UNITS



class FloatProperty(wxpg.FloatProperty):

    def __init__(self, label, name, value, min_value, max_value, increment, units=None):
        wxpg.FloatProperty.__init__(self, label, name, value)

        self._min_value = min_value
        self._max_value = max_value
        self._increment = increment

        if units is not None:
            self.SetAttribute(wxpg.PG_ATTR_UNITS, units)
    def GetDisplayedString(self):
        return str(self.m_value)

    def GetMinValue(self):
        return self._min_value

    def GetMaxValue(self):
        return self._max_value

    def GetIncrement(self):
        return self._increment

    def GetValue(self):
        return float(self.m_value)

    def DoGetEditorClass(self):
        return wxpg.PropertyGridInterface.GetEditorByName("FloatSpin")
