import wx


from .. import image as _image


class MixinBase:
    max_x: int = 0
    max_y: int = 0
    mode: int = 0
    overlay: wx.Bitmap = None
    background: wx.Bitmap = None
    draw_layer: wx.Bitmap = None
    tool_layer: wx.Bitmap = None
    tool_size: int = 0
    antialias: bool = True
    undo_layers: list = []
    capture_position = [0, 0]
    scale: float = 1.0
    dc: wx.MemoryDC = None
    pointer_cursor: wx.Cursor = None
    hand_cursor: wx.Cursor = _image.cursors.hand.cursor
    grab_cursor: wx.Cursor = _image.cursors.grab.cursor
    cross_cursor: wx.Cursor = _image.cursors.cross.cursor
    move_cursor: wx.Cursor = _image.cursors.move.cursor
    up_down_cursor: wx.Cursor = _image.cursors.up_down.cursor
    back_angle_cursor: wx.Cursor = _image.cursors.back_angle.cursor
    forward_angle_cursor: wx.Cursor = _image.cursors.forward_angle.cursor
    left_right_cursor: wx.Cursor = _image.cursors.left_right.cursor
    pencil_cursor: wx.Cursor = _image.cursors.pencil.cursor

    ID_POINTER_TOOL = wx.NewIdRef()
    ID_PAN_TOOL = wx.NewIdRef()
    ID_CROP_TOOL = wx.NewIdRef()
    ID_BRUSH_TOOL = wx.NewIdRef()
    ID_CAVITY_TOOL = wx.NewIdRef()
    ID_LINE_TOOL = wx.NewIdRef()
    ID_PENCIL_TOOL = wx.NewIdRef()
    ID_ERASER_TOOL = wx.NewIdRef()
    ID_RECT_TOOL = wx.NewIdRef()
    ID_CIRCLE_TOOL = wx.NewIdRef()
    ID_ANTIALIAS = wx.NewIdRef()
    ID_UNDO_CROP = wx.NewIdRef()

    def new_draw_layer(self):
        self.undo_layers.append(self.draw_layer)
        w, h = self.draw_layer.GetSize()
        buf = bytearray([0] * (w * h * 4))
        self.draw_layer = wx.Bitmap.FromBufferRGBA(w, h, buf)
        self.update_undo_layers()

    def _update(self):
        pass

    def Update(self):
        wx.Panel.Update(self)

    def Refresh(self):
        wx.Panel.Refresh(self)

    def HasCapture(self):
        return wx.Panel.HasCapture(self)

    def CaptureMouse(self):
        wx.Panel.CaptureMouse(self)

    def ReleaseMouse(self):
        wx.Panel.ReleaseMouse(self)

    def SetCursor(self, cursor):
        wx.Panel.SetCursor(self, cursor)

    def update_undo_layers(self):
        pass
