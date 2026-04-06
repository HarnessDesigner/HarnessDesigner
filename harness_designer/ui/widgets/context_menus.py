
import wx


class Rotate2DMenu(wx.Menu):

    def __init__(self, canvas, obj):
        wx.Menu.__init__(self)
        self.selected = obj
        self.canvas = canvas

        item = self.Append(wx.ID_ANY, 'Clockwise 90°')
        canvas.Bind(wx.EVT_MENU, self.on_pos_90, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Counter Clockwise 90°')
        canvas.Bind(wx.EVT_MENU, self.on_neg_90, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Rotate 180°')
        canvas.Bind(wx.EVT_MENU, self.on_pos_180, id=item.GetId())

    def on_pos_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_neg_90(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_pos_180(self, evt: wx.EVT_MENU):
        evt.Skip()


class Mirror2DMenu(wx.Menu):

    def __init__(self, canvas, obj):
        wx.Menu.__init__(self)
        self.selected = obj
        self.canvas = canvas

        item = self.Append(wx.ID_ANY, 'X')
        canvas.Bind(wx.EVT_MENU, self.on_x, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Y')
        canvas.Bind(wx.EVT_MENU, self.on_y, id=item.GetId())

    def on_x(self, evt: wx.EVT_MENU):
        evt.Skip()

    def on_y(self, evt: wx.EVT_MENU):
        evt.Skip()


class Rotate3DMenu(wx.Menu):

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


class Mirror3DMenu(wx.Menu):

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
