import wx

from . import canvas as _canvas
from . import dragging as _dragging
from . import object_picker as _object_picker
from . import arcball as _arcball
from ...geometry import point as _point

from ... import config as _config


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


wxEVT_GL_OBJECT_DRAG = wx.NewEventType()
EVT_GL_OBJECT_DRAG = wx.PyEventBinder(wxEVT_GL_OBJECT_DRAG, 0)


wxEVT_GL_LEFT_DOWN = wx.NewEventType()
EVT_GL_LEFT_DOWN = wx.PyEventBinder(wxEVT_GL_LEFT_DOWN, 0)

wxEVT_GL_LEFT_UP = wx.NewEventType()
EVT_GL_LEFT_UP = wx.PyEventBinder(wxEVT_GL_LEFT_UP, 0)

wxEVT_GL_LEFT_DCLICK = wx.NewEventType()
EVT_GL_LEFT_DCLICK = wx.PyEventBinder(wxEVT_GL_LEFT_DCLICK, 0)


wxEVT_GL_RIGHT_DOWN = wx.NewEventType()
EVT_GL_RIGHT_DOWN = wx.PyEventBinder(wxEVT_GL_RIGHT_DOWN, 0)

wxEVT_GL_RIGHT_UP = wx.NewEventType()
EVT_GL_RIGHT_UP = wx.PyEventBinder(wxEVT_GL_RIGHT_UP, 0)

wxEVT_GL_RIGHT_DCLICK = wx.NewEventType()
EVT_GL_RIGHT_DCLICK = wx.PyEventBinder(wxEVT_GL_RIGHT_DCLICK, 0)

wxEVT_GL_MIDDLE_DOWN = wx.NewEventType()
EVT_GL_MIDDLE_DOWN = wx.PyEventBinder(wxEVT_GL_MIDDLE_DOWN, 0)

wxEVT_GL_MIDDLE_UP = wx.NewEventType()
EVT_GL_MIDDLE_UP = wx.PyEventBinder(wxEVT_GL_MIDDLE_UP, 0)

wxEVT_GL_MIDDLE_DCLICK = wx.NewEventType()
EVT_GL_MIDDLE_DCLICK = wx.PyEventBinder(wxEVT_GL_MIDDLE_DCLICK, 0)

wxEVT_GL_AUX1_DOWN = wx.NewEventType()
EVT_GL_AUX1_DOWN = wx.PyEventBinder(wxEVT_GL_AUX1_DOWN, 0)

wxEVT_GL_AUX1_UP = wx.NewEventType()
EVT_GL_AUX1_UP = wx.PyEventBinder(wxEVT_GL_AUX1_UP, 0)

wxEVT_GL_AUX1_DCLICK = wx.NewEventType()
EVT_GL_AUX1_DCLICK = wx.PyEventBinder(wxEVT_GL_AUX1_DCLICK, 0)

wxEVT_GL_AUX2_DOWN = wx.NewEventType()
EVT_GL_AUX2_DOWN = wx.PyEventBinder(wxEVT_GL_AUX2_DOWN, 0)

wxEVT_GL_AUX2_UP = wx.NewEventType()
EVT_GL_AUX2_UP = wx.PyEventBinder(wxEVT_GL_AUX2_UP, 0)

wxEVT_GL_AUX2_DCLICK = wx.NewEventType()
EVT_GL_AUX2_DCLICK = wx.PyEventBinder(wxEVT_GL_AUX2_DCLICK, 0)


wxEVT_GL_DRAG = wx.NewEventType()
EVT_GL_DRAG = wx.PyEventBinder(wxEVT_GL_AUX2_DCLICK, 0)


class GLEvent(wx.CommandEvent):

    def __init__(self, evtType):
        wx.CommandEvent.__init__(self, evtType)
        self._mouse_pos = None
        self._world_pos = None
        self._mouse_button = wx.MOUSE_BTN_NONE

    def RightIsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_RIGHT)

    def LeftIsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_LEFT)

    def MiddleIsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_MIDDLE)

    def Aux1IsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_AUX1)

    def Aux2IsDown(self) -> bool:
        return bool(self._mouse_button & wx.MOUSE_BTN_AUX2)

    def SetMouseButtons(self, buttons):
        """
        :param buttons: OR'ed of
        wx.MOUSE_BTN_LEFT
        wx.MOUSE_BTN_RIGHT
        wx.MOUSE_BTN_MIDDLE
        wx.MOUSE_BTN_AUX1
        wx.MOUSE_BTN_AUX2
        :return:
        """
        self._mouse_button = buttons

    def GetPosition(self) -> _point.Point:
        return self._mouse_pos

    def SetPosition(self, pos: _point.Point):
        self._mouse_pos = pos

    def SetWorldPosition(self, pos: _point.Point):
        self._world_pos = pos

    def GetWorldPosition(self) -> _point.Point:
        return self._world_pos


class GLObjectEvent(GLEvent):

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
        self._is_motion = False
        self._mouse_pos = None
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

    def _process_mouse(self, code):
        for config, func in (
            (self.canvas.config.walk, self.canvas.Walk),
            (self.canvas.config.truck_pedestal, self.canvas.TruckPedestal),
            (self.canvas.config.rotate, self.canvas.Rotate),
            (self.canvas.config.pan_tilt, self.canvas.PanTilt),
            (self.canvas.config.zoom, self.canvas.Zoom),
            (self.canvas.config.reset, self.canvas.camera.Reset),
        ):
            if not config.mouse:
                continue

            if config.mouse & code:
                def _wrapper_func(c):

                    def _wrapper(dx, dy):
                        if c.mouse & MOUSE_SWAP_AXIS:
                            func(dy, dx)
                        else:
                            func(dx, dy)

                    return _wrapper

                return _wrapper_func(config)

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        refresh = False

        event = GLEvent(wxEVT_GL_LEFT_DOWN)
        if self._send_event(event, evt):
            cur_selected = self.canvas.get_selected()

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            with self.canvas:
                if selected is None:
                    if cur_selected is not None:
                        cur_selected.set_selected(False)
                        event = GLObjectEvent(wxEVT_GL_OBJECT_UNSELECTED)
                        event.SetGLObject(cur_selected)
                        refresh = True

                        if not self._send_event(event, evt):
                            cur_selected.set_selected(True)
                            refresh = False
                else:
                    if selected == cur_selected:
                        self._drag_obj = _dragging.DragObject(self.canvas,
                                                              selected)
                        refresh = False
                    else:
                        process_next_event = True

                        if cur_selected is not None:
                            cur_selected.set_selected(False)
                            event = GLObjectEvent(wxEVT_GL_OBJECT_UNSELECTED)
                            event.SetGLObject(cur_selected)

                            if not self._send_event(event, evt):
                                cur_selected.set_selected(True)
                                process_next_event = False

                        if process_next_event:
                            selected.set_selected(True)

                            event = GLObjectEvent(wxEVT_GL_OBJECT_SELECTED)
                            event.SetGLObject(selected)

                            if not self._send_event(event, evt):
                                selected.set_selected(False)

                        refresh = True

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        if refresh:
            self.canvas.Refresh(False)

    def _send_event(self, new_event: GLEvent, old_event: wx.MouseEvent) -> bool:
        position = _point.Point(*old_event.GetPosition())
        world_position = self.canvas.camera.UnprojectPoint(position)

        flags = 0

        if old_event.LeftIsDown():
            flags |= wx.MOUSE_BTN_LEFT

        if old_event.MiddleIsDown():
            flags |= wx.MOUSE_BTN_MIDDLE

        if old_event.RightIsDown():
            flags |= wx.MOUSE_BTN_RIGHT

        if old_event.Aux2IsDown():
            flags |= wx.MOUSE_BTN_AUX1

        if old_event.Aux2IsDown():
            flags |= wx.MOUSE_BTN_AUX2

        new_event.SetId(self.canvas.GetId())
        new_event.SetEventObject(self.canvas)
        new_event.SetPosition(position)
        new_event.SetWorldPosition(world_position)
        new_event.SetMouseButtons(flags)

        self.canvas.GetEventHandler().ProcessEvent(new_event)
        return new_event.ShouldPropagate()

    def on_left_up(self, evt: wx.MouseEvent):
        refresh = False

        event = GLEvent(wxEVT_GL_LEFT_UP)
        if self._send_event(event, evt):

            x, y = evt.GetPosition()
            mouse_pos = _point.Point(x, y)
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            if not self._is_motion and self._drag_obj is not None:
                if selected is not None and selected == cur_selected:
                    selected.set_selected(False)
                    event = GLObjectEvent(wxEVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)
                    refresh = True

                    if not self._send_event(event, evt):
                        selected.set_selected(True)
                        refresh = False

            if self._drag_obj is not None:
                self._drag_obj = None

        self._mouse_pos = None
        self._is_motion = False

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_left_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        refresh = False

        event = GLEvent(wxEVT_GL_LEFT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_ACTIVATED)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_middle_up(self, evt: wx.MouseEvent):
        refresh = False

        event = GLEvent(wxEVT_GL_MIDDLE_UP)
        if self._send_event(event, evt):
            if not self._is_motion:
                with self.canvas:
                    x, y = evt.GetPosition()
                    mouse_pos = _point.Point(x, y)
                    selected = _object_picker.find_object(mouse_pos,
                                                          self.canvas.objects_in_view,
                                                          self.canvas.camera)

                    if selected:
                        event = GLObjectEvent(wxEVT_GL_OBJECT_MIDDLE_CLICK)
                        event.SetGLObject(selected)
                        self._send_event(event, evt)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_middle_down(self, evt: wx.MouseEvent):
        self._is_motion = False
        refresh = False

        event = GLEvent(wxEVT_GL_MIDDLE_DOWN)
        self._send_event(event, evt)

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self._mouse_pos = _point.Point(x, y)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_middle_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        refresh = False

        event = GLEvent(wxEVT_GL_MIDDLE_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_MIDDLE_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):
        refresh = False

        event = GLEvent(wxEVT_GL_RIGHT_UP)
        if self._send_event(event, evt):

            with self.canvas:
                if self._is_motion:
                    if self._arcball is not None:
                        self._arcball = None
                        refresh = True
                else:
                    x, y = evt.GetPosition()
                    mouse_pos = _point.Point(x, y)

                    selected = _object_picker.find_object(mouse_pos,
                                                          self.canvas.objects_in_view,
                                                          self.canvas.camera)

                    if self._arcball is None:
                        if selected:
                            event = GLObjectEvent(wxEVT_GL_OBJECT_RIGHT_CLICK)
                            event.SetGLObject(selected)
                            self._send_event(event, evt)
                    else:
                        self._arcball = None
                        refresh = True

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):
        self._is_motion = False
        refresh = False

        x, y = evt.GetPosition()

        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos

        event = GLEvent(wxEVT_GL_RIGHT_DOWN)
        if self._send_event(event, evt):
            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            if selected and self.canvas.get_selected() == selected:
                self._arcball = _arcball.Arcball(self.canvas, selected)
                refresh = True

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_right_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        refresh = False

        event = GLEvent(wxEVT_GL_RIGHT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_RIGHT_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh(False)

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
        refresh = False

        if evt.Dragging():
            x, y = evt.GetPosition()
            mouse_pos = _point.Point(x, y)

            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            with self.canvas:
                if evt.LeftIsDown():
                    self._is_motion = True

                    if self._drag_obj is None:
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                    else:
                        self._drag_obj(delta)

                    refresh = True

                if evt.MiddleIsDown():
                    self._is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                    refresh = True

                if evt.RightIsDown():
                    self._is_motion = True

                    if self._arcball is not None:
                        self._arcball(mouse_pos)
                    else:
                        self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])

                    refresh = True

                if evt.Aux1IsDown():
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
                    refresh = True

                if evt.Aux2IsDown():
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])
                    refresh = True

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_aux1_up(self, evt: wx.MouseEvent):
        refresh = False

        if not self._is_motion:
            with self.canvas:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)
                selected = _object_picker.find_object(mouse_pos,
                                                      self.canvas.objects_in_view,
                                                      self.canvas.camera)

                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_AUX1_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh()

        evt.Skip()

    def on_aux1_down(self, evt: wx.MouseEvent):
        self._is_motion = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self._mouse_pos = _point.Point(x, y)

        evt.Skip()

    def on_aux1_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        selected = _object_picker.find_object(mouse_pos,
                                              self.canvas.objects_in_view,
                                              self.canvas.camera)

        refresh = False

        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_AUX1_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh()

        evt.Skip()

    def on_aux2_up(self, evt: wx.MouseEvent):
        refresh = False

        if not self._is_motion:
            with self.canvas:
                x, y = evt.GetPosition()
                mouse_pos = _point.Point(x, y)
                selected = _object_picker.find_object(mouse_pos,
                                                      self.canvas.objects_in_view,
                                                      self.canvas.camera)

                if selected:
                    event = GLObjectEvent(wxEVT_GL_OBJECT_AUX2_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh()

        evt.Skip()

    def on_aux2_down(self, evt: wx.MouseEvent):
        self._is_motion = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        x, y = evt.GetPosition()
        self._mouse_pos = _point.Point(x, y)

        evt.Skip()

    def on_aux2_dclick(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        selected = _object_picker.find_object(mouse_pos,
                                              self.canvas.objects_in_view,
                                              self.canvas.camera)

        refresh = False

        with self.canvas:
            if selected:
                event = GLObjectEvent(wxEVT_GL_OBJECT_AUX2_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh()

        evt.Skip()
