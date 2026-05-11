# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent

from . import canvas as _canvas
from . import dragging as _dragging
from . import object_picker as _object_picker
from . import arcball as _arcball
from ...geometry import point as _point
from ...shapes import sphere as _sphere
from ... import config as _config
from .. import events as _events
from ... import handlers as _handlers


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


def _qt_pos(qt_event) -> _point.Point:
    p = qt_event.position().toPoint()
    return _point.Point(p.x(), p.y())


def _qt_buttons_flag(qt_event) -> int:
    """Convert Qt mouse buttons bitmask to our internal BTN_* flags."""
    btns = qt_event.buttons()
    flags = 0
    if btns & Qt.LeftButton:
        flags |= _events.BTN_LEFT
    if btns & Qt.MiddleButton:
        flags |= _events.BTN_MIDDLE
    if btns & Qt.RightButton:
        flags |= _events.BTN_RIGHT
    if btns & Qt.XButton1:
        flags |= _events.BTN_AUX1
    if btns & Qt.XButton2:
        flags |= _events.BTN_AUX2
    return flags


class MouseHandler:

    def __init__(self, canvas: _canvas.Canvas):
        self.canvas = canvas

        self._drag_obj: _dragging.DragObject = None
        self._is_motion = False
        self._mouse_pos = None
        self._arcball: _arcball.Arcball = None
        self._gl_mouse_event: _events.GLEvent | _events.GLObjectEvent = None

        self._add_object_handler: _handlers.HandlerBase = None

        self._bundle_handler: _handlers.AddBundleHandler = None
        self._bundle_layout_handler: _handlers.AddBundleLayoutHandler = None
        self._cover_handler: _handlers.AddCoverHandler = None
        self._cpa_lock_handler: _handlers.AddCPALockHandler = None
        self._housing_handler: _handlers.AddHousingHandler = None
        self._seal_handler: _handlers.AddSealHandler = None
        self._splice_handler: _handlers.AddSpliceHandler = None
        self._terminal_handler: _handlers.AddTerminalHandler = None
        self._tpa_lock_handler: _handlers.AddTPALockHandler = None
        self._transition_handler: _handlers.AddTransitionHandler = None
        self._wire_handler: _handlers.AddWireHandler = None
        self._wire_layout_handler: _handlers.AddWireLayoutHandler = None
        self._wire_service_loop_handler: _handlers.AddWireServiceLoopHandler = None

        # Qt: install event filter instead of canvas.Bind()
        canvas.installEventFilter(self)

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    def eventFilter(self, obj, qt_event):
        if obj is not self.canvas:
            return False

        t = qt_event.type()

        if t == QEvent.MouseButtonPress:
            btn = qt_event.button()
            if btn == Qt.LeftButton:
                self.on_left_down(qt_event)
            elif btn == Qt.MiddleButton:
                self.on_middle_down(qt_event)
            elif btn == Qt.RightButton:
                self.on_right_down(qt_event)
            elif btn == Qt.XButton1:
                self.on_aux1_down(qt_event)
            elif btn == Qt.XButton2:
                self.on_aux2_down(qt_event)
            return False

        if t == QEvent.MouseButtonRelease:
            btn = qt_event.button()
            if btn == Qt.LeftButton:
                self.on_left_up(qt_event)
            elif btn == Qt.MiddleButton:
                self.on_middle_up(qt_event)
            elif btn == Qt.RightButton:
                self.on_right_up(qt_event)
            elif btn == Qt.XButton1:
                self.on_aux1_up(qt_event)
            elif btn == Qt.XButton2:
                self.on_aux2_up(qt_event)
            return False

        if t == QEvent.MouseButtonDblClick:
            btn = qt_event.button()
            if btn == Qt.LeftButton:
                self.on_left_dclick(qt_event)
            elif btn == Qt.MiddleButton:
                self.on_middle_dclick(qt_event)
            elif btn == Qt.RightButton:
                self.on_right_dclick(qt_event)
            elif btn == Qt.XButton1:
                self.on_aux1_dclick(qt_event)
            elif btn == Qt.XButton2:
                self.on_aux2_dclick(qt_event)
            return False

        if t == QEvent.MouseMove:
            self.on_mouse_motion(qt_event)
            return False

        if t == QEvent.Wheel:
            self.on_mouse_wheel(qt_event)
            return False

        # Mouse capture lost: Qt sends QEvent.MouseButtonRelease with no
        # button held when the grab is broken externally.  For explicit
        # capture-lost notification we use QWidget.mouseGrabber() == None
        # after a grab was active.  The canvas calls this directly when
        # needed — see Canvas.changeEvent override (not required here).
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    @property
    def active_event(self) -> "_events.GLEvent | _events.GLObjectEvent | None":
        return self._gl_mouse_event

    def _send_event(self, new_event: "_events.GLEvent | _events.GLObjectEvent",
                    qt_event) -> bool:
        position = _qt_pos(qt_event)
        world_position = self.canvas.camera.UnprojectPoint(position)

        flags = _qt_buttons_flag(qt_event)

        new_event.SetId(id(self.canvas))
        new_event.SetEventObject(self.canvas)
        new_event.SetPosition(position)
        new_event.SetWorldPosition(world_position)
        new_event.SetMouseButtons(flags)

        if flags:
            self._gl_mouse_event = new_event
        else:
            self._gl_mouse_event = None

        # Emit the matching canvas signal.
        # The signal name is the lowercase version of the event type name,
        # e.g. EVT_GL_LEFT_DOWN → gl_left_down.
        signal_name = new_event.event_type.name.lower()
        signal = getattr(self.canvas, signal_name, None)
        if signal is not None:
            signal.emit(new_event)

        return not new_event.skipped()

    def _send_capture_lost(self):
        event = _events.GLCaptureLostEvent(_events.EVT_GL_CAPTURE_LOST)
        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        self.canvas.gl_capture_lost.emit(event)

        if not event.skipped():
            return

        if self._drag_obj is not None:
            self._drag_obj.delete()
            self._drag_obj = None

        self._arcball = None
        self._is_motion = False
        if self.canvas.hasMouseTracking():   # if grab was active, release
            pass  # grab is released by Qt automatically on button release

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def on_left_down(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        event = _events.GLEvent(_events.EVT_GL_LEFT_DOWN)
        if self._send_event(event, evt):
            return

        self.canvas.grabMouse()

    def on_left_up(self, evt):
        refresh = False

        event = _events.GLEvent(_events.EVT_GL_LEFT_UP)
        if self._send_event(event, evt):

            mouse_pos = _qt_pos(evt)
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            if not self._is_motion:
                if cur_selected is None and selected is not None:
                    selected.set_selected(True)

                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        selected.set_selected(False)

                elif selected is None and cur_selected is not None:
                    cur_selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        cur_selected.set_selected(True)

                elif (
                    selected is not None and
                    cur_selected is not None and
                    selected == cur_selected
                ):
                    selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(selected)

                    if not self._send_event(event, evt):
                        selected.set_selected(True)

                elif (
                    selected is not None and
                    cur_selected is not None and
                    selected != cur_selected
                ):
                    cur_selected.set_selected(False)
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    event.SetGLObject(cur_selected)

                    if not self._send_event(event, evt):
                        cur_selected.set_selected(True)
                    else:
                        selected.set_selected(True)

                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                        event.SetGLObject(selected)

                        if not self._send_event(event, evt):
                            selected.set_selected(False)

                refresh = True

            if self._drag_obj is not None:
                self._drag_obj.delete()
                self._drag_obj = None

        self._mouse_pos = None
        self._is_motion = False

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    def on_left_dclick(self, evt):
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_LEFT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_ACTIVATED)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    def on_middle_up(self, evt):
        refresh = False

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_UP)
        if self._send_event(event, evt):
            if not self._is_motion:
                with self.canvas:
                    mouse_pos = _qt_pos(evt)
                    selected = _object_picker.find_object(mouse_pos,
                                                          self.canvas.objects_in_view,
                                                          self.canvas.camera)

                    if selected:
                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_CLICK)
                        event.SetGLObject(selected)
                        self._send_event(event, evt)

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    def on_middle_down(self, evt):
        self._is_motion = False

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DOWN)
        self._send_event(event, evt)

        self.canvas.grabMouse()

        self._mouse_pos = _qt_pos(evt)

    def on_middle_dclick(self, evt):
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    def on_right_up(self, evt):
        refresh = False

        event = _events.GLEvent(_events.EVT_GL_RIGHT_UP)
        if self._send_event(event, evt):

            with self.canvas:
                if self._is_motion:
                    if self._arcball is not None:
                        self._arcball = None
                        refresh = True
                else:
                    mouse_pos = _qt_pos(evt)

                    selected = _object_picker.find_object(mouse_pos,
                                                          self.canvas.objects_in_view,
                                                          self.canvas.camera)

                    if self._arcball is None:
                        if selected:
                            event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_CLICK)
                            event.SetGLObject(selected)
                            self._send_event(event, evt)
                    else:
                        self._arcball = None
                        refresh = True

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    def on_right_down(self, evt):
        self._is_motion = False

        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DOWN)
        if self._send_event(event, evt):
            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            if selected and self.canvas.get_selected() == selected:
                self._arcball = _arcball.Arcball(self.canvas, selected)
                self.canvas.update()

        self.canvas.grabMouse()

    def on_right_dclick(self, evt):
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)
            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    def on_mouse_wheel(self, evt):
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self._process_mouse(MOUSE_WHEEL)(delta, 0.0)
        self.canvas.update()

    def on_mouse_motion(self, evt):
        refresh = False

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MOUSE_MOVE)
        if not self._send_event(event, evt):
            return

        btns = evt.buttons()
        if btns != Qt.NoButton:   # dragging
            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()

            selected = _object_picker.find_object(mouse_pos,
                                                  self.canvas.objects_in_view,
                                                  self.canvas.camera)

            with self.canvas:
                if btns & Qt.LeftButton:
                    self._is_motion = True

                    if self._drag_obj is None:
                        if (
                            selected is not None and
                            cur_selected is not None and
                            selected == cur_selected
                        ):
                            self._drag_obj = _dragging.DragObject(self.canvas, selected)
                        else:
                            self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                            refresh = True
                    else:
                        self._drag_obj(delta)
                        refresh = True

                if btns & Qt.MiddleButton:
                    self._is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                    refresh = True

                if btns & Qt.RightButton:
                    self._is_motion = True

                    if self._arcball is not None:
                        self._arcball(mouse_pos)
                    else:
                        self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])

                    refresh = True

                if btns & Qt.XButton1:
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
                    refresh = True

                if btns & Qt.XButton2:
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])
                    refresh = True

        if refresh:
            self.canvas.update()

    def on_aux1_up(self, evt):
        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(mouse_pos,
                                                      self.canvas.objects_in_view,
                                                      self.canvas.camera)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    def on_aux1_down(self, evt):
        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    def on_aux1_dclick(self, evt):
        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(mouse_pos,
                                              self.canvas.objects_in_view,
                                              self.canvas.camera)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

    def on_aux2_up(self, evt):
        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(mouse_pos,
                                                      self.canvas.objects_in_view,
                                                      self.canvas.camera)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    def on_aux2_down(self, evt):
        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    def on_aux2_dclick(self, evt):
        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(mouse_pos,
                                              self.canvas.objects_in_view,
                                              self.canvas.camera)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)
