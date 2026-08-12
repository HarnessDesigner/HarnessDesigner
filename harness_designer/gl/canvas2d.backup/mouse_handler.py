# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

from PySide6 import QtCore
from PySide6.QtWidgets import QMenu

from ... import config as _config
from ...geometry import point as _point
from .. import events as _events
from .. import object_picker as _object_picker
from ..canvas3d import rotation_rings as _rotation_rings
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas as _canvas


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


@_check_types.do
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


@_check_types.do
def _qt_buttons_flag(qt_event) -> int:
    """Convert Qt button flags to our BTN_* bitmask."""
    btns = qt_event.buttons()
    flags = _events.BTN_NONE
    if btns & QtCore.Qt.MouseButton.LeftButton:
        flags |= _events.BTN_LEFT
    if btns & QtCore.Qt.MouseButton.RightButton:
        flags |= _events.BTN_RIGHT
    if btns & QtCore.Qt.MouseButton.MiddleButton:
        flags |= _events.BTN_MIDDLE
    if btns & QtCore.Qt.MouseButton.XButton1:
        flags |= _events.BTN_AUX1
    if btns & QtCore.Qt.MouseButton.XButton2:
        flags |= _events.BTN_AUX2
    return flags


class MouseHandler(QtCore.QObject):

    canvas: "_canvas.Canvas" = None

    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`MouseHandler` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """

        super().__init__()
        self.canvas = canvas

        self._mouse_pos: _point.Point = None
        self._is_motion = False

        # Rotate-gizmo drag state -- shared by every 2D-plane editor (see
        # gl.canvas2d.rotation_ring.RotationRing's module docstring).
        # Entering/exiting "rotation mode" itself lives on Canvas
        # (rotation_gizmo_target is the single source of truth for whether
        # it's active) -- this is just the continuous-drag bookkeeping for
        # while the handle is being dragged.
        self._rotate_drag_active = False
        self._rotate_start_value = 0.0
        self._rotate_center = None
        self._rotate_prev_phi = None
        self._rotate_total = 0.0

        # Set by on_right_down() when that exact press entered rotation
        # mode -- on_right_up() checks this to avoid also running its own
        # normal click handling for the same press.
        self._right_down_entered_rotation = False

        canvas.installEventFilter(self)

    # ------------------------------------------------------------------
    # Rotate-gizmo hit-testing / drag
    # ------------------------------------------------------------------

    @_check_types.do
    def _rotation_handle_hit(self, mouse_pos: _point.Point) -> bool:
        """Return whether *mouse_pos* (screen coordinates) hits the active
        rotate gizmo's grab handle.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        :returns: ``True`` if the handle was hit.
        :rtype: bool
        """
        handle_world = self.canvas.rotation_gizmo_handle_world_pos()
        if handle_world is None:
            return False

        screen = self.canvas.camera.world_to_screen(
            _point.Point(handle_world.x, handle_world.z))
        dx = float(screen.x) - float(mouse_pos.x)
        dz = float(screen.y) - float(mouse_pos.y)

        return math.hypot(dx, dz) <= _rotation_rings.HANDLE_PICK_TOLERANCE

    @_check_types.do
    def _rotate_center_screen(self, target) -> tuple:
        """Return the active gizmo's *target*'s screen-space center.

        :param target: The object/anchor currently in rotation mode.
        :returns: ``(screen_x, screen_y)``.
        :rtype: tuple[float, float]
        """
        world = _point.Point(target.position.x, target.position.z)
        screen = self.canvas.camera.world_to_screen(world)
        return float(screen.x), float(screen.y)

    @staticmethod
    @_check_types.do
    def _rotate_screen_phi(mouse_pos: _point.Point, center_x: float,
                           center_z: float) -> float:
        """Return the math-orientation angle of the cursor around
        ``(center_x, center_z)``.

        Screen Y grows downward, negated for counter-clockwise-positive
        math. No camera-facing sign flip is needed here -- every
        2D-plane editor only ever has one fixed top-down viewing
        direction.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        :param center_x: Rotation center, screen X.
        :type center_x: float
        :param center_z: Rotation center, screen Y.
        :type center_z: float
        :returns: Polar angle, radians.
        :rtype: float
        """
        return math.atan2(-(float(mouse_pos.y) - center_z),
                          float(mouse_pos.x) - center_x)

    @_check_types.do
    def _arm_rotate_drag(self, mouse_pos: _point.Point) -> None:
        """Arm a continuous rotate-drag starting at *mouse_pos*.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        self._rotate_drag_active = True
        self._rotate_start_value = self.canvas.rotation_gizmo_degrees
        self._rotate_center = self._rotate_center_screen(
            self.canvas.rotation_gizmo_target)
        self._rotate_prev_phi = self._rotate_screen_phi(
            mouse_pos, *self._rotate_center)
        self._rotate_total = 0.0

    @_check_types.do
    def _rotation_snap_angle(self) -> float:
        """Return the rotation-drag snap increment in degrees, or ``0``
        for free rotation.

        Overridden per editor -- the schematic editor forces a hard
        90-degree detent, the peg board editor's detent is optional/
        user-configurable (``Config.editor_pegboard.rotation_ring.
        snap_enable``/``.snap_angle``). The drag mechanics that apply
        whatever this returns (:meth:`_update_rotate_drag`) are identical
        either way -- only the value differs.

        :returns: Snap increment in degrees, or ``0`` for free rotation.
        :rtype: float
        """
        return 0.0

    @_check_types.do
    def _update_rotate_drag(self, mouse_pos: _point.Point) -> None:
        """Update the in-progress rotate-drag from the current mouse
        position -- writes immediately through the target's bound
        ``Angle`` (see ``Canvas.update_rotation_drag``).

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        phi = self._rotate_screen_phi(mouse_pos, *self._rotate_center)

        step = math.atan2(math.sin(phi - self._rotate_prev_phi),
                          math.cos(phi - self._rotate_prev_phi))
        self._rotate_prev_phi = phi
        self._rotate_total += step

        new_value = _rotation_rings.wrap_angle(
            self._rotate_start_value + math.degrees(self._rotate_total))

        snap = self._rotation_snap_angle()
        if snap:
            new_value = _rotation_rings.wrap_angle(
                round(round(new_value / snap) * snap, 2))

        self.canvas.update_rotation_drag(new_value)

    @_check_types.do
    def _send_event(self, event, qt_event):
        """Populate event fields and emit the named canvas signal."""
        mouse_pos = _qt_pos(qt_event)
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        flags = _qt_buttons_flag(qt_event)

        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        event.SetPosition(mouse_pos)
        event.SetWorldPosition(world_pos)
        event.SetMouseButtons(flags)

        getattr(self.canvas, event.GetType()).emit(event)

        return event

    @_check_types.do
    def eventFilter(self, obj, qt_event):
        """Execute the event filter operation.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        :param qt_event: Value for ``qt_event``.
        :type qt_event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if obj is not self.canvas:
            return False

        try:
            t = qt_event.type()
        except:  # NOQA
            return False

        if t == QtCore.QEvent.Type.MouseButtonPress:
            btn = qt_event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_down(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_down(qt_event)
            return False

        if t == QtCore.QEvent.Type.MouseButtonRelease:
            btn = qt_event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_up(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_up(qt_event)
            return False

        if t == QtCore.QEvent.Type.MouseButtonDblClick:
            btn = qt_event.button()
            if btn == QtCore.Qt.MouseButton.LeftButton:
                self.on_left_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.MiddleButton:
                self.on_middle_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.RightButton:
                self.on_right_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton1:
                self.on_aux1_dclick(qt_event)
            elif btn == QtCore.Qt.MouseButton.XButton2:
                self.on_aux2_dclick(qt_event)
            return False

        if t == QtCore.QEvent.Type.MouseMove:
            self.on_mouse_motion(qt_event)
            return False

        if t == QtCore.QEvent.Type.Wheel:
            self.on_mouse_wheel(qt_event)
            return False

        return False

    @_check_types.do
    def _process_mouse(self, code):
        for config, func in (
            (self.canvas.config.pan, self.canvas.Pan),
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

    def on_left_down(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DOWN), evt)

    def on_left_up(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_UP), evt)

    def on_left_dclick(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DCLICK), evt)

    def on_right_down(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DOWN), evt)

    def on_right_up(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_UP), evt)

    def on_right_dclick(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DCLICK), evt)

    def on_middle_down(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_DOWN), evt)

    def on_middle_up(self, evt):
        self._mouse_pos = _qt_pos(evt)
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_UP), evt)
        self.canvas.releaseMouse()

    def on_middle_dclick(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK), evt)

    def on_aux1_up(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_UP), evt)
        self.canvas.releaseMouse()

    def on_aux1_down(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_DOWN), evt)
        self.canvas.releaseMouse()

    def on_aux1_dclick(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_DCLICK), evt)
        self.canvas.releaseMouse()

    def on_aux2_up(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_UP), evt)
        self.canvas.releaseMouse()

    def on_aux2_down(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_DOWN), evt)
        self.canvas.releaseMouse()

    def on_aux2_dclick(self, evt):
        # TODO : add code for generic handling.
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_DCLICK), evt)
        self.canvas.releaseMouse()

    def on_mouse_motion(self, evt):
        refresh = False

        btns = evt.buttons()
        if btns != QtCore.Qt.MouseButton.NoButton:
            mouse_pos = _qt_pos(evt)

            if self._mouse_pos is None:
                self._mouse_pos = mouse_pos

            delta = mouse_pos - self._mouse_pos
            self._mouse_pos = mouse_pos

            with self.canvas:
                if btns & QtCore.Qt.MouseButton.LeftButton:
                    self._is_motion = True

                    if self._rotate_drag_active:
                        self._update_rotate_drag(mouse_pos)
                    else:
                        # TODO : add code for generic object-drag handling.
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])

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

        self._send_event(_events.GLEvent(_events.EVT_GL_MOUSE_MOVE), evt)

        if refresh:
            self.canvas.update()

    def on_mouse_wheel(self, evt):
        mouse_pos = _qt_pos(evt)
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self.canvas.camera.zoom_at_point(mouse_pos, delta)
        self.canvas.update()
