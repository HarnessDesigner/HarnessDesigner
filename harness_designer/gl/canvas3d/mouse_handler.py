import wx

from . import canvas as _canvas
from . import dragging as _dragging
from . import object_picker as _object_picker
from . import arcball as _arcball
from ...geometry import point as _point

from ... import config as _config
from .. import events as _events


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

        canvas.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_mouse_capture_lost)

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

        event = _events.GLEvent(_events.wxEVT_GL_LEFT_DOWN)
        if self._send_event(event, evt):
            return

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        if refresh:
            self.canvas.Refresh(False)

    def _send_event(self, new_event: _events.GLEvent, old_event: wx.MouseEvent) -> bool:
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

    def on_mouse_capture_lost(self, evt: wx.MouseCaptureLostEvent):
        self._drag_obj = None
        self._arcball = None
        self._is_motion = False
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_left_up(self, evt: wx.MouseEvent):
        refresh = False

        event = _events.GLEvent(_events.wxEVT_GL_LEFT_UP)
        if self._send_event(event, evt):

            x, y = evt.GetPosition()
            mouse_pos = _point.Point(x, y)
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            if not self._is_motion:
                if cur_selected is None and selected is not None:
                    selected.set_selected(True)

                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_SELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        selected.set_selected(False)

                elif selected is None and cur_selected is not None:
                    cur_selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        cur_selected.set_selected(True)

                elif (
                    selected is not None and
                    cur_selected is not None and
                    selected == cur_selected
                ):
                    selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        selected.set_selected(True)

                elif (
                    selected is not None and
                    cur_selected is not None and
                    selected != cur_selected
                ):
                    cur_selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(cur_selected)

                    if not self._send_event(event, evt):
                        cur_selected.set_selected(True)
                    else:
                        selected.set_selected(True)

                        event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_SELECTED)
                        event.SetGLObject(selected)

                        if not self._send_event(event, evt):
                            selected.set_selected(False)

                refresh = True

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

        event = _events.GLEvent(_events.wxEVT_GL_LEFT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_ACTIVATED)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_middle_up(self, evt: wx.MouseEvent):
        refresh = False

        event = _events.GLEvent(_events.wxEVT_GL_MIDDLE_UP)
        if self._send_event(event, evt):
            if not self._is_motion:
                with self.canvas:
                    x, y = evt.GetPosition()
                    mouse_pos = _point.Point(x, y)
                    selected = _object_picker.find_object(mouse_pos,
                                                          self.canvas.objects_in_view,
                                                          self.canvas.camera)

                    if selected:
                        event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_MIDDLE_CLICK)
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

        event = _events.GLEvent(_events.wxEVT_GL_MIDDLE_DOWN)
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

        event = _events.GLEvent(_events.wxEVT_GL_MIDDLE_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_MIDDLE_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):
        refresh = False

        event = _events.GLEvent(_events.wxEVT_GL_RIGHT_UP)
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
                            event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_RIGHT_CLICK)
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

        event = _events.GLEvent(_events.wxEVT_GL_RIGHT_DOWN)
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

        event = _events.GLEvent(_events.wxEVT_GL_RIGHT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_RIGHT_DCLICK)
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

            cur_selected = self.canvas.get_selected()

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            with self.canvas:
                if evt.LeftIsDown():
                    self._is_motion = True

                    if self._drag_obj is None:
                        if (
                            selected is not None and
                            cur_selected is not None and
                            selected == cur_selected
                        ):
                            self._drag_obj = _dragging.DragObject(self.canvas, selected)
                            refresh = False
                        else:
                            self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                            refresh = True
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
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_AUX1_CLICK)
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
                event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_AUX1_DCLICK)
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
                    event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_AUX2_CLICK)
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
                event = _events.GLObjectEvent(_events.wxEVT_GL_OBJECT_AUX2_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

        if refresh:
            self.canvas.Refresh()

        evt.Skip()
