# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import math

from PySide6 import QtCore

from . import canvas as _canvas
from . import dragging as _dragging
from . import object_picker as _object_picker
from . import rotation_rings as _rotation_rings
from ...geometry import point as _point
from ...shapes import sphere as _sphere
from ... import config as _config
from ... import utils as _utils
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

_EPSILON = 1e-6


def _qt_pos(qt_event) -> _point.Point:
    """Execute the qt pos operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param qt_event: Value for ``qt_event``.
    :type qt_event: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: :class:`_point.Point`
    """
    p = qt_event.position().toPoint()
    return _point.Point(p.x(), p.y())


def _qt_buttons_flag(qt_event) -> int:
    """Convert Qt mouse buttons bitmask to our internal BTN_* flags."""
    btns = qt_event.buttons()
    flags = 0
    if btns & QtCore.Qt.MouseButton.LeftButton:
        flags |= _events.BTN_LEFT
    if btns & QtCore.Qt.MouseButton.MiddleButton:
        flags |= _events.BTN_MIDDLE
    if btns & QtCore.Qt.MouseButton.RightButton:
        flags |= _events.BTN_RIGHT
    if btns & QtCore.Qt.MouseButton.XButton1:
        flags |= _events.BTN_AUX1
    if btns & QtCore.Qt.MouseButton.XButton2:
        flags |= _events.BTN_AUX2
    return flags


class MouseHandler:
    """Represent a mouse handler in :mod:`harness_designer.gl.canvas3d.mouse_handler`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas: _canvas.Canvas):
        """Initialise the :class:`MouseHandler` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        self.canvas = canvas

        self._drag_obj: _dragging.DragObject = None
        self._is_motion = False
        self._mouse_pos = None

        # Angle mode: rotation ring gizmo + active handle drag.
        # NOTE: the previous arcball rotation (arcball.py) is no longer wired
        # up — pending a decision to either expose it as a user choice or
        # remove it entirely.
        self._rotation_rings: _rotation_rings.RotationRings = None
        self._rotate_drag: _rotation_rings.DragRotate = None

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

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    def handle_event(self, event):
        """Handle the event.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        t = event.type()

        if t == QtCore.QEvent.Type.MouseButtonPress:
            btn = event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_down(event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_down(event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_down(event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_down(event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_down(event)

            return False

        if t == QtCore.QEvent.Type.MouseButtonRelease:
            btn = event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_up(event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_up(event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_up(event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_up(event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_up(event)
            return False

        if t == QtCore.QEvent.Type.MouseButtonDblClick:
            btn = event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_dclick(event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_dclick(event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_dclick(event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_dclick(event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_dclick(event)
            return False

        if t == QtCore.QEvent.Type.MouseMove:
            self.on_mouse_motion(event)
            return False

        if t == QtCore.QEvent.Type.Wheel:
            self.on_mouse_wheel(event)
            return False

        # Mouse capture lost: Qt sends QEvent.Type.MouseButtonRelease with no
        # button held when the grab is broken externally.  For explicit
        # capture-lost notification we use QWidget.mouseGrabber() == None
        # after a grab was active.  The canvas calls this directly when
        # needed — see Canvas.changeEvent override (not required here).
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick_object(self, mouse_pos):
        """Pick a scene object, ignoring the rotation ring gizmo."""
        objects = self.canvas.objects_in_view

        if self._rotation_rings is not None:
            objects = [o for o in objects if o is not self._rotation_rings]

        return _object_picker.find_object(mouse_pos, objects, self.canvas.camera)

    def _exit_angle_mode(self):
        """Remove the rotation rings and end any active rotation drag."""
        self._rotate_drag = None

        if self._rotation_rings is not None:
            self._rotation_rings.delete()
            self._rotation_rings = None

    def _process_mouse(self, code):
        """Execute the process mouse operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param code: Value for ``code``.
        :type code: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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
                    """Execute the wrapper func operation.

                    UNKNOWN details are inferred from the callable name and signature.

                    :param c: Value for ``c``.
                    :type c: UNKNOWN
                    :returns: Return value. UNKNOWN details.
                    :rtype: UNKNOWN
                    """
                    def _wrapper(dx, dy):
                        """Execute the wrapper operation.

                        UNKNOWN details are inferred from the callable name and signature.

                        :param dx: Value for ``dx``.
                        :type dx: UNKNOWN
                        :param dy: Value for ``dy``.
                        :type dy: UNKNOWN
                        """
                        if c.mouse & MOUSE_SWAP_AXIS:
                            func(dy, dx)
                        else:
                            func(dx, dy)
                    return _wrapper

                return _wrapper_func(config)

        def _do_nothing_func(_, __):
            """Execute the do nothing func operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param _: Value for ``_``.
            :type _: UNKNOWN
            :param __: Value for ``__``.
            :type __: UNKNOWN
            """
            pass

        return _do_nothing_func

    @property
    def active_event(self) -> "_events.GLEvent | _events.GLObjectEvent | None":
        """Return the active event.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: _events.GLEvent | _events.GLObjectEvent | None
        """
        return self._gl_mouse_event

    def _send_event(self, new_event: "_events.GLEvent | _events.GLObjectEvent",
                    qt_event) -> bool:
        """Execute the send event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param new_event: Value for ``new_event``.
        :type new_event: _events.GLEvent | _events.GLObjectEvent
        :param qt_event: Value for ``qt_event``.
        :type qt_event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """

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

        getattr(self.canvas, new_event.GetType()).emit(new_event)

        return new_event.ShouldPropagate()

    def _send_capture_lost(self):
        """Execute the send capture lost operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        event = _events.GLCaptureLostEvent(_events.EVT_GL_CAPTURE_LOST)
        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        self.canvas.gl_capture_lost.emit(event)

        if not event.ShouldPropagate():
            return

        if self._drag_obj is not None:
            self._drag_obj.delete()
            self._drag_obj = None

        self._exit_angle_mode()
        self._is_motion = False
        if self.canvas.hasMouseTracking():   # if grab was active, release
            pass  # grab is released by Qt automatically on button release

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def on_left_down(self, evt):
        """Handle the left down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        if self._rotation_rings is not None:
            selected = self.canvas.get_selected()
            if selected is None:
                # Selection vanished out from under angle mode (e.g. via the
                # object browser) — drop the rings.
                self._exit_angle_mode()
            else:
                axis = self._rotation_rings.pick_handle(mouse_pos, self.canvas.camera)
                if axis is not None:
                    self._rotate_drag = _rotation_rings.DragRotate(
                        self.canvas, selected, axis, self._rotation_rings)

        event = _events.GLEvent(_events.EVT_GL_LEFT_DOWN)
        if self._send_event(event, evt):
            return

        self.canvas.grabMouse()

    def on_left_up(self, evt):
        """Handle the left up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        refresh = False

        event = _events.GLEvent(_events.EVT_GL_LEFT_UP)
        if self._send_event(event, evt):

            mouse_pos = _qt_pos(evt)
            self._mouse_pos = mouse_pos

            if self._rotation_rings is not None:
                # Angle mode consumes left clicks: ending a handle drag keeps
                # the rings; a click (no motion) anywhere that is not a grab
                # handle exits angle mode. Selection is left untouched.
                if self._rotate_drag is not None:
                    self._rotate_drag = None
                elif not self._is_motion:
                    axis = self._rotation_rings.pick_handle(
                        mouse_pos, self.canvas.camera)
                    if axis is None:
                        self._exit_angle_mode()

                self._mouse_pos = None
                self._is_motion = False
                self.canvas.releaseMouse()
                self.canvas.update()
                return

            cur_selected = self.canvas.get_selected()

            selected = self._pick_object(mouse_pos)

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
        """Handle the left dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_LEFT_DCLICK)
        if self._send_event(event, evt):
            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_ACTIVATED)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    def on_middle_up(self, evt):
        """Handle the middle up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        refresh = False

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_UP)
        if self._send_event(event, evt):
            if not self._is_motion:
                with self.canvas:
                    mouse_pos = _qt_pos(evt)
                    selected = _object_picker.find_object(
                        mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

                    if selected:
                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_CLICK)
                        event.SetGLObject(selected)
                        self._send_event(event, evt)

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    def on_middle_down(self, evt):
        """Handle the middle down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._is_motion = False

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DOWN)
        self._send_event(event, evt)

        self.canvas.grabMouse()

        self._mouse_pos = _qt_pos(evt)

    def on_middle_dclick(self, evt):
        """Handle the middle dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    def on_right_up(self, evt):
        """Handle the right up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        refresh = False

        event = _events.GLEvent(_events.EVT_GL_RIGHT_UP)
        if self._send_event(event, evt):

            with self.canvas:
                if not self._is_motion:
                    mouse_pos = _qt_pos(evt)

                    selected = self._pick_object(mouse_pos)

                    if selected and selected != self.canvas.get_selected():
                        # Context menu only for objects that are not the
                        # current selection — right-clicking the selected
                        # object is the angle-mode gesture (on_right_down).
                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_CLICK)
                        event.SetGLObject(selected)
                        self._send_event(event, evt)
                    else:
                        refresh = True

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    def on_right_down(self, evt):
        """Handle the right down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._is_motion = False

        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DOWN)
        if self._send_event(event, evt):
            selected = self._pick_object(mouse_pos)

            # Right-click on the selected object enters angle mode; the
            # context menu (on_right_up) is reserved for unselected objects.
            if selected and self.canvas.get_selected() == selected:
                if self._rotation_rings is None:
                    self._rotation_rings = _rotation_rings.RotationRings(
                        self.canvas, selected)
                    self.canvas.update()

        self.canvas.grabMouse()

    def on_right_dclick(self, evt):
        """Handle the right dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    def on_mouse_wheel(self, evt):
        """Handle the mouse wheel event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0

        if self.canvas.config.walk.mouse & MOUSE_WHEEL:
            self._orient_to_mouse_on_focal_plane(_qt_pos(evt), delta)

        self._process_mouse(MOUSE_WHEEL)(delta, 0.0)
        self.canvas.update()

    def _orient_to_mouse_on_focal_plane(self, mouse_pos: _point.Point, wheel_delta: float) -> None:
        def _norm(values) -> float:
            return math.sqrt(sum(v * v for v in values))

        camera = self.canvas.camera
        target = _utils.get_position_on_focal_plane(mouse_pos, camera)
        camera_pos = camera.position
        focal_pos = camera.focal_position

        current_forward = (
            focal_pos.x - camera_pos.x,
            focal_pos.y - camera_pos.y,
            focal_pos.z - camera_pos.z
        )
        desired_forward = (
            target.x - camera_pos.x,
            target.y - camera_pos.y,
            target.z - camera_pos.z
        )

        current_norm = _norm(current_forward)
        desired_norm = _norm(desired_forward)

        if current_norm < _EPSILON or desired_norm < _EPSILON:
            return

        current_forward = tuple(v / current_norm for v in current_forward)
        desired_forward = tuple(v / desired_norm for v in desired_forward)

        current_xz = (current_forward[0], current_forward[2])
        desired_xz = (desired_forward[0], desired_forward[2])

        current_xz_norm = _norm(current_xz)
        desired_xz_norm = _norm(desired_xz)

        yaw_delta = 0.0
        if current_xz_norm > _EPSILON and desired_xz_norm > _EPSILON:
            current_xz = tuple(v / current_xz_norm for v in current_xz)
            desired_xz = tuple(v / desired_xz_norm for v in desired_xz)
            dot = max(-1.0, min(1.0, (current_xz[0] * desired_xz[0]) + (current_xz[1] * desired_xz[1])))
            cross = (current_xz[0] * desired_xz[1]) - (current_xz[1] * desired_xz[0])
            yaw_delta = -math.degrees(math.atan2(cross, dot))

        current_pitch = math.degrees(math.atan2(current_forward[1], current_xz_norm))
        desired_pitch = math.degrees(math.atan2(desired_forward[1], desired_xz_norm))
        pitch_delta = desired_pitch - current_pitch

        if abs(yaw_delta) < _EPSILON and abs(pitch_delta) < _EPSILON:
            return

        walk_cfg = self.canvas.config.walk
        step_distance = abs(wheel_delta) * walk_cfg.sensitivity * walk_cfg.speed
        if step_distance < _EPSILON:
            return

        angular_step_size = math.degrees(math.atan2(step_distance, current_norm))
        largest_rotation_component = max(abs(yaw_delta), abs(pitch_delta))

        if largest_rotation_component > angular_step_size > _EPSILON:
            scale = angular_step_size / largest_rotation_component
            yaw_delta *= scale
            pitch_delta *= scale

        camera.PanTilt(yaw_delta / 6, pitch_delta / 6)

    def on_mouse_motion(self, evt):
        """Handle the mouse motion event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        refresh = False

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MOUSE_MOVE)
        if not self._send_event(event, evt):
            return

        btns = evt.buttons()
        if btns != QtCore.Qt.MouseButton.NoButton:
            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()

            selected = self._pick_object(mouse_pos)

            with self.canvas:
                if btns & QtCore.Qt.MouseButton.LeftButton:
                    self._is_motion = True

                    if self._rotate_drag is not None:
                        self._rotate_drag(mouse_pos)
                        refresh = True
                    elif self._rotation_rings is not None:
                        # Angle mode: a drag not on a grab handle moves the
                        # camera; object move-dragging is disabled.
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                        refresh = True
                    elif self._drag_obj is None:
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

                if btns & QtCore.Qt.MouseButton.MiddleButton:
                    self._is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                    refresh = True

                if btns & QtCore.Qt.MouseButton.RightButton:
                    self._is_motion = True

                    self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])

                    refresh = True

                if btns & QtCore.Qt.MouseButton.XButton1:
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
                    refresh = True

                if btns & QtCore.Qt.MouseButton.XButton2:
                    self._is_motion = True
                    self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])
                    refresh = True

        if refresh:
            self.canvas.update()

    def on_aux1_up(self, evt):
        """Handle the aux 1 up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(
                    mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    def on_aux1_down(self, evt):
        """Handle the aux 1 down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    def on_aux1_dclick(self, evt):
        """Handle the aux 1 dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(
            mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

    def on_aux2_up(self, evt):
        """Handle the aux 2 up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(
                    mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    def on_aux2_down(self, evt):
        """Handle the aux 2 down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    def on_aux2_dclick(self, evt):
        """Handle the aux 2 dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(
            mouse_pos, self.canvas.objects_in_view, self.canvas.camera)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)
