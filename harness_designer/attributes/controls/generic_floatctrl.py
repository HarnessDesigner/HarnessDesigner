
import wx
from ... import utils
from ...wrappers.decimal import Decimal as _decimal


class GenericFloatCtrl(wx.Panel):

    def __init__(self, parent, label, suffix=None):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, min=0.0, max=999.90, inc=0.1, size=(100, -1))

        if suffix is None:
            sizer = utils.HSizer(self, label, self.ctrl)
        else:
            sizer = utils.HSizer(self, label, self.ctrl, suffix)

        self.SetSizer(sizer)

    def SetValue(self, value: _decimal) -> None:
        self.ctrl.SetValue(float(value))

    def GetValue(self) -> _decimal:
        return _decimal(self.ctrl.GetValue())
