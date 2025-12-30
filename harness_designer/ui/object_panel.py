import wx
from ..widgets import foldpanelbar
from ..wrappers.decimal import Decimal as _decimal
from ..database.project_db import pjt_boot as _pjt_boot
from ..database.project_db import pjt_bundle as _pjt_bundle


class ObjectSelectedPanel(wx.Panel):

    def __init__(self, mainframe):
        self.mainframe = mainframe
        wx.Panel.__init__(self, mainframe, wx.ID_ANY, style=wx.BORDER_NONE)
        self.fpb = foldpanelbar.FoldPanelBar(self, wx.ID_ANY, agwStyle=foldpanelbar.FPB_SINGLE_FOLD | foldpanelbar.FPB_VERTICAL)

        cbs = foldpanelbar.CaptionBarStyle()
        cbs.SetCaptionStyle(foldpanelbar.CAPTIONBAR_GRADIENT_H)
        cbs.SetFirstColour(wx.Colour(160, 0, 255, 255))
        cbs.SetSecondColour(wx.Colour(0, 0, 0, 255))
        cbs.SetCaptionColour(wx.Colour(200, 200, 200, 255))
        self.fpb.ApplyCaptionStyleAll(cbs)

    def ClearPanels(self):
        for i in range(self.fpb.GetCount() - 1, -1, -1):
            self.fpb.DeleteFoldPanel(self.fpb.GetFoldPanel(i))


class FloatCtrl(wx.BoxSizer):
    
    def __init__(self, parent, label, min_val, max_val):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        
        st = wx.StaticText(parent, wx.ID_ANY, label=label)
        self.ctrl = wx.SpinCtrlDouble(parent, wx.ID_ANY, value=str(min_val), initial=min_val, min=min_val, max=max_val, inc=0.1)
        
        self.Add(st, 0, wx.ALL, 5)
        self.Add(self.ctrl, 0, wx.ALL, 5)
        
    def Bind(self, event, handler):
        self.ctrl.Bind(event, handler)
        
    def SetValue(self, value: _decimal):
        self.ctrl.SetValue(float(value))
        
    def GetValue(self) -> _decimal:
        return _decimal(self.ctrl.GetValue())


class Boot:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)
        
        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)
        
        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)
        
        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()
        
    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()
        
    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()
        
    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()
        
        
class Bundle:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        '''
        Layer 1 (core)
            Diameter
            Wire 1:
                Circuit:
                Size (AWG):
                Size (mm2):
                Outside Diameter:
                Is Filler:
        '''

        self.position = fpb.AddFoldPanel('Position')
        self.start_x = FloatCtrl(self.position, 'Start X:', min_val=-9999.9, max_val=9999.9)
        self.start_y = FloatCtrl(self.position, 'Start Y:', min_val=-9999.9, max_val=9999.9)
        self.start_z = FloatCtrl(self.position, 'Start Z:', min_val=-9999.9, max_val=9999.9)

        self.end_x = FloatCtrl(self.position, 'End X:', min_val=-9999.9, max_val=9999.9)
        self.end_y = FloatCtrl(self.position, 'End Y:', min_val=-9999.9, max_val=9999.9)
        self.end_z = FloatCtrl(self.position, 'End Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.start_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_start_x)
        self.start_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_start_y)
        self.start_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_start_z)

        self.end_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_end_x)
        self.end_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_end_y)
        self.end_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_end_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_start_x(self, evt):
        self.db_obj.start_point3d.point.x = self.start_x.GetValue()
        evt.Skip()

    def on_start_y(self, evt):
        self.db_obj.start_point3d.point.y = self.start_y.GetValue()
        evt.Skip()

    def on_start_z(self, evt):
        self.db_obj.start_point3d.point.z = self.start_z.GetValue()
        evt.Skip()

    def on_end_x(self, evt):
        self.db_obj.stop_point3d.point.x = self.end_x.GetValue()
        evt.Skip()

    def on_end_y(self, evt):
        self.db_obj.stop_point3d.point.y = self.end_y.GetValue()
        evt.Skip()

    def on_end_z(self, evt):
        self.db_obj.stop_point3d.point.z = self.end_z.GetValue()
        evt.Skip()


class Cover:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class CPALock:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class Housing:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class Seal:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class Splice:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class Terminal:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        '''
        Settings
            Is Visible
            Is Circuit Start
            Allowed Voltage Drop
            Load
            Volts
            Seal

        
        '''
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class TPALock:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.scale = fpb.AddFoldPanel('Scale')
        self.scale_x = FloatCtrl(self.scale, 'X:', min_val=0.1, max_val=99.9)
        self.scale_y = FloatCtrl(self.scale, 'Y:', min_val=0.1, max_val=99.9)
        self.scale_z = FloatCtrl(self.scale, 'Z:', min_val=0.1, max_val=99.9)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.scale_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_x)
        self.scale_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_y)
        self.scale_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_scale_z)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_scale_x(self, evt):
        self.db_obj.scale.x = self.scale_x.GetValue()
        evt.Skip()

    def on_scale_y(self, evt):
        self.db_obj.scale.y = self.scale_y.GetValue()
        evt.Skip()

    def on_scale_z(self, evt):
        self.db_obj.scale.z = self.scale_z.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class Transition:
    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class Wire:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.position = fpb.AddFoldPanel('Position')
        self.start_x = FloatCtrl(self.position, 'Start X:', min_val=-9999.9, max_val=9999.9)
        self.start_y = FloatCtrl(self.position, 'Start Y:', min_val=-9999.9, max_val=9999.9)
        self.start_z = FloatCtrl(self.position, 'Start Z:', min_val=-9999.9, max_val=9999.9)

        self.end_x = FloatCtrl(self.position, 'End X:', min_val=-9999.9, max_val=9999.9)
        self.end_y = FloatCtrl(self.position, 'End Y:', min_val=-9999.9, max_val=9999.9)
        self.end_z = FloatCtrl(self.position, 'End Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.start_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_start_x)
        self.start_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_start_y)
        self.start_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_start_z)

        self.end_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_end_x)
        self.end_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_end_y)
        self.end_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_end_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_start_x(self, evt):
        self.db_obj.start_point3d.point.x = self.start_x.GetValue()
        evt.Skip()

    def on_start_y(self, evt):
        self.db_obj.start_point3d.point.y = self.start_y.GetValue()
        evt.Skip()

    def on_start_z(self, evt):
        self.db_obj.start_point3d.point.z = self.start_z.GetValue()
        evt.Skip()

    def on_end_x(self, evt):
        self.db_obj.stop_point3d.point.x = self.end_x.GetValue()
        evt.Skip()

    def on_end_y(self, evt):
        self.db_obj.stop_point3d.point.y = self.end_y.GetValue()
        evt.Skip()

    def on_end_z(self, evt):
        self.db_obj.stop_point3d.point.z = self.end_z.GetValue()
        evt.Skip()


class WireMarker:

    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()


class WireServiceLoop:
    
    def __init__(self, fpb: foldpanelbar.FoldPanelBar, db_obj: _pjt_boot.PJTBoot):
        self.db_obj = db_obj
        self.settings = fpb.AddFoldPanel('Settings')
        self.visible = wx.CheckBox(self.settings, wx.ID_ANY, 'Visible')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.visible, 0, wx.ALL, 10)
        self.settings.SetSizer(sizer)

        self.rotate = fpb.AddFoldPanel('Rotate')
        self.rotate_x = FloatCtrl(self.rotate, 'X Angle:', min_val=0.0, max_val=359.9)
        self.rotate_y = FloatCtrl(self.rotate, 'Y Angle:', min_val=0.0, max_val=359.9)
        self.rotate_z = FloatCtrl(self.rotate, 'Z Angle:', min_val=0.0, max_val=359.9)

        self.position = fpb.AddFoldPanel('Position')
        self.position_x = FloatCtrl(self.position, 'X:', min_val=-9999.9, max_val=9999.9)
        self.position_y = FloatCtrl(self.position, 'Y:', min_val=-9999.9, max_val=9999.9)
        self.position_z = FloatCtrl(self.position, 'Z:', min_val=-9999.9, max_val=9999.9)

        self.visible.Bind(wx.EVT_CHECKBOX, self.on_visible)

        self.rotate_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_x)
        self.rotate_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_y)
        self.rotate_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rotate_z)

        self.position_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_x)
        self.position_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_y)
        self.position_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_position_z)

    def on_visible(self, evt):
        self.db_obj.is_visible = self.visible.GetValue()
        evt.Skip()

    def on_rotate_x(self, evt):
        self.db_obj.angl3d.x = self.rotate_x.GetValue()
        evt.Skip()

    def on_rotate_y(self, evt):
        self.db_obj.angle3d.y = self.rotate_y.GetValue()
        evt.Skip()

    def on_rotate_z(self, evt):
        self.db_obj.angle3d.z = self.rotate_z.GetValue()
        evt.Skip()

    def on_position_x(self, evt):
        self.db_obj.point3d.point.x = self.position_x.GetValue()
        evt.Skip()

    def on_position_y(self, evt):
        self.db_obj.point3d.point.y = self.position_y.GetValue()
        evt.Skip()

    def on_position_z(self, evt):
        self.db_obj.point3d.point.z = self.position_z.GetValue()
        evt.Skip()

