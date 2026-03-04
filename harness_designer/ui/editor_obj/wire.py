'''
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


'''