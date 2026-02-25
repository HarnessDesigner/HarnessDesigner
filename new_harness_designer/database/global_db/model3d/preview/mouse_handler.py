import wx

from . import Preview as _Preview
from ...geometry import point as _point

from ... import config as _config

Config = _config.Config

MOUSE_NONE = _config.MOUSE_NONE
MOUSE_LEFT = _config.MOUSE_LEFT
MOUSE_MIDDLE = _config.MOUSE_MIDDLE
MOUSE_RIGHT = _config.MOUSE_RIGHT
MOUSE_AUX1 = _config.MOUSE_AUX1
MOUSE_AUX2 = _config.MOUSE_AUX2
MOUSE_WHEEL = _config.MOUSE_WHEEL

MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_WHEEL_AXIS = _config.MOUSE_REVERSE_WHEEL_AXIS
MOUSE_SWAP_AXIS = _config.MOUSE_SWAP_AXIS


class MouseHandler:

    def __init__(self, canvas: _Preview):
        self.canvas = canvas

        self.mouse_pos = None

        canvas.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        canvas.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)

        canvas.Bind(wx.EVT_MIDDLE_UP, self.on_middle_up)
        canvas.Bind(wx.EVT_MIDDLE_DOWN, self.on_middle_down)

        canvas.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        canvas.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)

        canvas.Bind(wx.EVT_MOUSE_AUX1_UP, self.on_aux1_up)
        canvas.Bind(wx.EVT_MOUSE_AUX1_DOWN, self.on_aux1_down)

        canvas.Bind(wx.EVT_MOUSE_AUX2_UP, self.on_aux2_up)
        canvas.Bind(wx.EVT_MOUSE_AUX2_DOWN, self.on_aux2_down)

        canvas.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        canvas.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

    def _process_mouse(self, code):
        for config, func in (
            (Config.walk, self.canvas.Walk),
            (Config.truck_pedestal, self.canvas.TruckPedestal),
            (Config.reset, self.canvas.camera.Reset),
            (Config.rotate, self.canvas.Rotate),
            (Config.pan_tilt, self.canvas.PanTilt),
            (Config.zoom, self.canvas.Zoom)
        ):
            if config.mouse is None:
                continue

            if config.mouse & code:

                def _wrapper(dx, dy):
                    if config.mouse & MOUSE_SWAP_AXIS:
                        func(dy, dx)
                    else:
                        func(dx, dy)

                return _wrapper

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        self.mouse_pos = mouse_pos

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

    def on_left_up(self, evt: wx.MouseEvent):
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_middle_up(self, evt: wx.MouseEvent):
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_middle_down(self, evt: wx.MouseEvent):
        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = _point.Point(x, y)

        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):
        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()

        mouse_pos = _point.Point(x, y)
        self.mouse_pos = mouse_pos

        evt.Skip()

    def on_mouse_wheel(self, evt: wx.MouseEvent):
        if evt.GetWheelRotation() > 0:
            delta = 1.0
        else:
            delta = -1.0

        self._process_mouse(MOUSE_WHEEL)(delta, 0.0)

        self.canvas.Refresh(False)
        evt.Skip()

    def on_mouse_motion(self, evt: wx.MouseEvent):
        if evt.Dragging():
            x, y = evt.GetPosition()
            mouse_pos = _point.Point(x, y)

            if self.mouse_pos is None:
                self.mouse_pos = mouse_pos

            delta = mouse_pos - self.mouse_pos
            self.mouse_pos = mouse_pos

            if evt.LeftIsDown():
                self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
            if evt.MiddleIsDown():
                self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
            if evt.RightIsDown():
                self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])
            if evt.Aux1IsDown():
                self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
            if evt.Aux2IsDown():
                self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])

            self.canvas.Refresh(False)

        evt.Skip()

    def on_aux1_up(self, evt: wx.MouseEvent):
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_aux1_down(self, evt: wx.MouseEvent):
        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = _point.Point(x, y)

        evt.Skip()

    def on_aux2_up(self, evt: wx.MouseEvent):
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_aux2_down(self, evt: wx.MouseEvent):
        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = _point.Point(x, y)

        evt.Skip()
