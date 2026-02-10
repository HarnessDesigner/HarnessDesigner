import wx

from . import canvas as _canvas
from . import dragging as _dragging
from . import object_picker as _object_picker
from . import arcball as _arcball
from .geometry import point as _point

from . import config as _config
from . import debug as _debug

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


wxEVT_GL_OBJECT_SELECTED = wx.NewEventType()
EVT_GL_OBJECT_SELECTED = wx.PyEventBinder(wxEVT_GL_OBJECT_SELECTED, 0)

wxEVT_GL_OBJECT_UNSELECTED = wx.NewEventType()
EVT_GL_OBJECT_UNSELECTED = wx.PyEventBinder(wxEVT_GL_OBJECT_UNSELECTED, 0)

wxEVT_GL_OBJECT_ACTIVATED = wx.NewEventType()
EVT_GL_OBJECT_ACTIVATED = wx.PyEventBinder(wxEVT_GL_OBJECT_ACTIVATED, 0)

wxEVT_GL_OBJECT_RIGHT_CLICK = wx.NewEventType()
EVT_GL_OBJECT_RIGHT_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_RIGHT_CLICK, 0)

wxEVT_GL_OBJECT_RIGHT_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_RIGHT_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_RIGHT_DCLICK, 0)

wxEVT_GL_OBJECT_MIDDLE_CLICK = wx.NewEventType()
EVT_GL_OBJECT_MIDDLE_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_MIDDLE_CLICK, 0)

wxEVT_GL_OBJECT_MIDDLE_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_MIDDLE_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_MIDDLE_DCLICK, 0)

wxEVT_GL_OBJECT_AUX1_CLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX1_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX1_CLICK, 0)

wxEVT_GL_OBJECT_AUX1_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX1_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX1_DCLICK, 0)

wxEVT_GL_OBJECT_AUX2_CLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX2_CLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX2_CLICK, 0)

wxEVT_GL_OBJECT_AUX2_DCLICK = wx.NewEventType()
EVT_GL_OBJECT_AUX2_DCLICK = wx.PyEventBinder(wxEVT_GL_OBJECT_AUX2_DCLICK, 0)


class GLObjectEvent(wx.CommandEvent):

    def __init__(self, evtType):
        wx.CommandEvent.__init__(self, evtType)
        self._gl_object = None

    def GetGLObject(self):
        return not self._gl_object

    def SetGLObject(self, obj):
        self._gl_object = obj


class MouseHandler:

    def __init__(self, canvas: _canvas.Canvas):
        self.canvas = canvas

        self._drag_obj: _dragging.DragObject = None
        self.is_motion = False
        self.mouse_pos = None
        self._arcball: _arcball.Arcball = None

        canvas.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        canvas.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        canvas.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)

        canvas.Bind(wx.EVT_MIDDLE_UP, self.on_middle_up)
        canvas.Bind(wx.EVT_MIDDLE_DOWN, self.on_middle_down)
        canvas.Bind(wx.EVT_MIDDLE_DCLICK, self.on_middle_dclick)

        canvas.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        canvas.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        canvas.Bind(wx.EVT_RIGHT_DCLICK, self.on_right_dclick)

        canvas.Bind(wx.EVT_MOUSE_AUX1_UP, self.on_aux1_up)
        canvas.Bind(wx.EVT_MOUSE_AUX1_DOWN, self.on_aux1_down)
        canvas.Bind(wx.EVT_MOUSE_AUX1_DCLICK, self.on_aux1_dclick)

        canvas.Bind(wx.EVT_MOUSE_AUX2_UP, self.on_aux2_up)
        canvas.Bind(wx.EVT_MOUSE_AUX2_DOWN, self.on_aux2_down)
        canvas.Bind(wx.EVT_MOUSE_AUX2_DCLICK, self.on_aux2_dclick)

        canvas.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        canvas.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

    @_debug.logfunc
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

    @_debug.logfunc
    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        self.mouse_pos = mouse_pos
        self.is_motion = False

        refresh = False
        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

        if selected:
            with self.canvas:
                if self.canvas.selected == selected:
                    self._drag_obj = _dragging.DragObject(self.canvas, selected)
                    refresh = True

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        if refresh:
            self.canvas.Refresh(False)

    @_debug.logfunc
    def on_left_up(self, evt: wx.MouseEvent):
        refresh = False

        with self.canvas:
            if self.is_motion:
                if self._drag_obj is not None:
                    self._drag_obj = None

                    refresh = True
            else:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)  # NOQA

                if self._drag_obj is not None:
                    self._drag_obj = None
                    refresh = True

                selected = _object_picker.find_object(mouse_pos, self.canvas._objects)
                if selected:
                    if self.canvas.selected == selected:
                        selected.set_selected(False)
                        self.canvas.selected = None
                        event = GLObjectEvent(wxEVT_GL_OBJECT_UNSELECTED)
                        event.SetId(self.canvas.GetId())
                        event.SetEventObject(self.canvas)
                        event.SetGLObject(selected)
                        self.canvas.GetEventHandler().ProcessEvent(event)
                        refresh = True

                    else:
                        if self.canvas.selected is not None:
                            tmp_selected = self.canvas.selected
                            self.canvas.selected.set_selected(False)
                            self.canvas.selected = None

                            event = GLObjectEvent(wxEVT_GL_OBJECT_UNSELECTED)
                            event.SetId(self.canvas.GetId())
                            event.SetEventObject(self.canvas)
                            event.SetGLObject(tmp_selected)
                            self.canvas.GetEventHandler().ProcessEvent(event)

                        self.canvas.selected = selected
                        selected.set_selected(True)

                        event = GLObjectEvent(wxEVT_GL_OBJECT_SELECTED)
                        event.SetId(self.canvas.GetId())
                        event.SetEventObject(self.canvas)
                        event.SetGLObject(selected)
                        self.canvas.GetEventHandler().ProcessEvent(event)
                        refresh = True

        self.mouse_pos = None
        self.is_motion = False

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_left_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        refresh = False

        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)
        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_ACTIVATED)
                event.SetId(self.canvas.GetId())
                event.SetEventObject(self.canvas)
                event.SetGLObject(selected)
                self.canvas.GetEventHandler().ProcessEvent(event)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_middle_up(self, evt: wx.MouseEvent):
        refresh = False

        if not self.is_motion:
            with self.canvas:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)
                selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_MIDDLE_CLICK)
                    event.SetId(self.canvas.GetId())
                    event.SetEventObject(self.canvas)
                    event.SetGLObject(selected)
                    self.canvas.GetEventHandler().ProcessEvent(event)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_middle_down(self, evt: wx.MouseEvent):
        self.is_motion = False
        refresh = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = _point.Point(x, y)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_middle_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        refresh = False

        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)
        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_MIDDLE_DCLICK)
                event.SetId(self.canvas.GetId())
                event.SetEventObject(self.canvas)
                event.SetGLObject(selected)
                self.canvas.GetEventHandler().ProcessEvent(event)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_right_up(self, evt: wx.MouseEvent):
        refresh = False

        with self.canvas:
            if self.is_motion:
                if self._arcball is not None:
                    self._arcball = None
                    refresh = True
            else:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)

                selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

                if self._arcball is None:
                    if selected:
                        event = GLObjectEvent(wxEVT_GL_OBJECT_RIGHT_CLICK)
                        event.SetId(self.canvas.GetId())
                        event.SetEventObject(self.canvas)
                        event.SetGLObject(selected)
                        self.canvas.GetEventHandler().ProcessEvent(event)
                else:
                    self._arcball = None
                    refresh = True

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_right_down(self, evt: wx.MouseEvent):
        self.is_motion = False
        refresh = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()

        mouse_pos = _point.Point(x, y)
        self.mouse_pos = mouse_pos

        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)
        if selected and self.canvas.selected == selected:
            self._arcball = _arcball.Arcball(self.canvas, selected)
            refresh = True

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_right_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        refresh = False

        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)
        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_RIGHT_DCLICK)
                event.SetId(self.canvas.GetId())
                event.SetEventObject(self.canvas)
                event.SetGLObject(selected)
                self.canvas.GetEventHandler().ProcessEvent(event)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_mouse_wheel(self, evt: wx.MouseEvent):
        if evt.GetWheelRotation() > 0:
            delta = 1.0
        else:
            delta = -1.0

        self._process_mouse(MOUSE_WHEEL)(delta, 0.0)

        self.canvas.Refresh(False)
        evt.Skip()

    @_debug.logfunc
    def on_mouse_motion(self, evt: wx.MouseEvent):
        refresh = False

        if evt.Dragging():
            x, y = evt.GetPosition()
            mouse_pos = _point.Point(x, y)

            if self.mouse_pos is None:
                self.mouse_pos = mouse_pos

            delta = mouse_pos - self.mouse_pos
            self.mouse_pos = mouse_pos

            with self.canvas:
                if evt.LeftIsDown():
                    self.is_motion = True

                    if self._drag_obj is None:
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                    else:
                        self._drag_obj(delta)

                    refresh = True

                if evt.MiddleIsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                    refresh = True

                if evt.RightIsDown():
                    self.is_motion = True

                    if self._arcball is not None:
                        self._arcball(mouse_pos)
                    else:
                        self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])

                    refresh = True

                if evt.Aux1IsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
                    refresh = True

                if evt.Aux2IsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])
                    refresh = True

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    @_debug.logfunc
    def on_aux1_up(self, evt: wx.MouseEvent):
        refresh = False

        if not self.is_motion:
            with self.canvas:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)
                selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_AUX1_CLICK)
                    event.SetId(self.canvas.GetId())
                    event.SetEventObject(self.canvas)
                    event.SetGLObject(selected)
                    self.canvas.GetEventHandler().ProcessEvent(event)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh()

        evt.Skip()

    @_debug.logfunc
    def on_aux1_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = _point.Point(x, y)

        evt.Skip()

    @_debug.logfunc
    def on_aux1_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

        refresh = False

        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_AUX1_DCLICK)
                event.SetId(self.canvas.GetId())
                event.SetEventObject(self.canvas)
                event.SetGLObject(selected)
                self.canvas.GetEventHandler().ProcessEvent(event)

        if refresh:
            self.canvas.Refresh()

        evt.Skip()

    @_debug.logfunc
    def on_aux2_up(self, evt: wx.MouseEvent):
        refresh = False

        if not self.is_motion:
            with self.canvas:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)
                selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_AUX2_CLICK)
                    event.SetId(self.canvas.GetId())
                    event.SetEventObject(self.canvas)
                    event.SetGLObject(selected)
                    self.canvas.GetEventHandler().ProcessEvent(event)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh()

        evt.Skip()

    @_debug.logfunc
    def on_aux2_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = _point.Point(x, y)

        evt.Skip()

    @_debug.logfunc
    def on_aux2_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        selected = _object_picker.find_object(mouse_pos, self.canvas._objects)

        refresh = False

        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_AUX2_DCLICK)
                event.SetId(self.canvas.GetId())
                event.SetEventObject(self.canvas)
                event.SetGLObject(selected)
                self.canvas.GetEventHandler().ProcessEvent(event)

        if refresh:
            self.canvas.Refresh()

        evt.Skip()
