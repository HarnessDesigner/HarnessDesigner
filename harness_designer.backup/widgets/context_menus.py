
import wx


class RotateMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.selected = selected
        self.canvas = canvas

        item = self.Append(wx.ID_ANY, 'X +90°')
        canvas.Bind(wx.EVT_MENU, self.on_x_pos_90, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'X -90°')
        canvas.Bind(wx.EVT_MENU, self.on_x_neg_90, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Y +90°')
        canvas.Bind(wx.EVT_MENU, self.on_y_pos_90, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Y -90°')
        canvas.Bind(wx.EVT_MENU, self.on_y_neg_90, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Z +90°')
        canvas.Bind(wx.EVT_MENU, self.on_z_pos_90, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Z -90°')
        canvas.Bind(wx.EVT_MENU, self.on_z_neg_90, id=item.GetId())

    def on_x_pos_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_x_neg_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_y_pos_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_y_neg_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_z_pos_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_z_neg_90(self, evt: wx.EVT_MENU):
        evt.Skip()


class MirrorMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.selected = selected
        self.canvas = canvas

        item = self.Append(wx.ID_ANY, 'X')
        canvas.Bind(wx.EVT_MENU, self.on_x, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Y')
        canvas.Bind(wx.EVT_MENU, self.on_y, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Z')
        canvas.Bind(wx.EVT_MENU, self.on_z, id=item.GetId())

    def on_x(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_y(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_z(self, evt: wx.EVT_MENU):
        evt.Skip()
