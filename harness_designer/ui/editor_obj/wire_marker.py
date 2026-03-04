'''

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


'''