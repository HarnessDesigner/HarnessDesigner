
import wx
from ... import utils


class DimensionCtrl(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        sb_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, 'Dimensions')
        sb = sb_sizer.GetStaticBox()

        self.length_ctrl = wx.SpinCtrlDouble(sb, wx.ID_ANY, value='0.0', initial=0.0, min=0.0, max=999.90, inc=0.1, size=(100, -1))
        self.width_ctrl = wx.SpinCtrlDouble(sb, wx.ID_ANY, value='0.0', initial=0.0, min=0.0, max=999.90, inc=0.1, size=(100, -1))
        self.height_ctrl = wx.SpinCtrlDouble(sb, wx.ID_ANY, value='0.0', initial=0.0, min=0.0, max=999.90, inc=0.1, size=(100, -1))

        length_sizer = utils.HSizer(sb, 'Length:', self.length_ctrl, 'mm')
        width_sizer = utils.HSizer(sb, 'Width:', self.width_ctrl, 'mm')
        height_sizer = utils.HSizer(sb, 'Height:', self.height_ctrl, 'mm')

        sb_sizer.Add(length_sizer)
        sb_sizer.Add(width_sizer)
        sb_sizer.Add(height_sizer)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sb_sizer)

        self.SetSizer(sizer)

    def SetValue(self, length: float, width: float, height: float) -> None:
        self.length_ctrl.SetValue(length)
        self.width_ctrl.SetValue(width)
        self.height_ctrl.SetValue(height)

    def GetValue(self) -> tuple[float, float, float]:
        return (self.length_ctrl.GetValue(),
                self.width_ctrl.GetValue(),
                self.height_ctrl.GetValue())
