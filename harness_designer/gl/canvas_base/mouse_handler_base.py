# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Editor-agnostic mouse dispatch.

This module knows nothing about ``CanvasBase._drag_handler`` /
``CanvasBase._rotation_handler`` and never calls them directly. Those
handlers (see ``drag_handler_base.py`` / ``rotation_handler_base.py``)
instead register themselves as listeners on the same GL Qt signals this
module already emits via :meth:`MouseHandlerBase._send_event`
(``gl_left_down`` / ``gl_mouse_move`` / ``gl_left_up`` /
``gl_right_down`` / ``gl_capture_lost``) -- exactly the same pattern
``ui.mainframe.MainFrame`` already uses for its own ``_obj_handler``
(e.g. an in-progress ``AddWireHandler`` two-click placement). When a
handler takes authority over an event it calls ``evt.StopPropagation()``,
which every default-behavior call site below is already gated on via
``event.ShouldPropagate()`` (returned by ``_send_event``) -- so a drag
or rotation in progress transparently suppresses this module's own
camera-pan / object-selection logic without this module needing to ask
about it.
"""

import math
from typing import TYPE_CHECKING

from PySide6 import QtCore

from .. import object_picker as _object_picker
from ...geometry import point as _point
from ... import config as _config
from .. import events as _events
from ...objects import housing as _housing
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas_base as _canvas_base


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


class MouseHandlerBase:
    """Represent a mouse handler in :mod:`harness_designer.gl.canvas3d.mouse_handler`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase"):
        """Initialise the :class:`MouseHandler` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas_base.CanvasBase`
        """
        self.canvas = canvas
        self.config = self.canvas.config.input

        self._is_motion = False
        self._mouse_pos = None
        self._active_cavity_housing = None

        self._gl_mouse_event: _events.GLEvent | _events.GLObjectEvent | None = None

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    @_check_types.do
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

    @_check_types.do
    def _pick_exclusions(self) -> tuple:
        """Objects that must never be pick-eligible -- gizmo overlays drawn
        on top of the scene (the 3D canvas's focal-target indicator, the
        active rotation-rings gizmo). Checked generically (``getattr``
        with a ``None`` default) rather than via a per-canvas override,
        since not every canvas has these -- schematic/pegboard just fall
        through to the empty tuple.

        The rotation rings themselves are excluded here, but their grab
        handles are not affected -- handle-grabbing goes through
        RotationRings.pick_handle(), a separate code path that never
        consults this method.
        """
        exclusions = []

        focal_target = getattr(self.canvas, '_focal_target', None)
        if focal_target is not None:
            exclusions.append(focal_target)

        rotation_rings = getattr(self.canvas, '_rotation_rings', None)
        if rotation_rings is not None:
            exclusions.append(rotation_rings)

        return tuple(exclusions)

    @_check_types.do
    def _pick_object(self, mouse_pos, current_selection=None):
        """Pick a scene object, ignoring anything :meth:`_pick_exclusions`
        reports (e.g. an active rotation gizmo overlay)."""
        objects = self.canvas.objects_in_view

        exclusions = self._pick_exclusions()
        if exclusions:
            objects = [o for o in objects if o not in exclusions]

        return _object_picker.find_object(
            mouse_pos, objects, self.canvas.camera,
            self._get_view_object, current_selection=current_selection)

    @_check_types.do
    def _process_mouse(self, code):
        """Execute the process mouse operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param code: Value for ``code``.
        :type code: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        if (
            self.config.truck_pedestal.mouse is not None and
            self.config.truck_pedestal.mouse & code
        ):

            def _wrapper(dx, dy):

                if self.config.truck_pedestal.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                if self.config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.truck_pedestal.sensitivity
                self.canvas.camera.TruckPedestal(
                    dx * sens, dy * sens, self.config.truck_pedestal.speed)

            return _wrapper

        if (
            self.config.rotate.mouse is not None and
            self.config.rotate.mouse & code
        ):

            def _wrapper(dx, dy):

                if self.config.rotate.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                if self.config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.rotate.sensitivity
                self.canvas.camera.Rotate(dx * sens, dy * sens)

            return _wrapper

        if (
            self.config.pan_tilt.mouse is not None and
            self.config.pan_tilt.mouse & code
        ):

            def _wrapper(dx, dy):

                if self.config.pan_tilt.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                if self.config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.pan_tilt.sensitivity
                self.canvas.camera.PanTilt(dx * sens, dy * sens)

            return _wrapper

        if (
            self.config.dolly.mouse is not None and
            self.config.dolly.mouse & code
        ):
            def _wrapper(dx, dy):

                if self.config.dolly.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                sens = self.config.dolly.sensitivity
                self.canvas.camera.Dolly(dx * sens)

            return _wrapper

        if (
            self.config.reset.mouse is not None and
            self.config.reset.mouse & code
        ):

            def _wrapper(_, __):
                self.canvas.camera.Reset()

            return _wrapper

        if (
            self.config.walk.mouse is not None and
            self.config.walk.mouse & code
        ):
            def _wrapper(dx, dy):
                if dy == 0.0:
                    self.canvas.PanTilt(dx * 6.0, 0.0)
                    return

                if self.config.walk.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                look_dx = dx
                if self.config.walk.mouse & MOUSE_REVERSE_X_AXIS:
                    dx = -dx

                if self.config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
                    dy = -dy

                sens = self.config.walk.sensitivity
                self.canvas.camera.Walk(
                    dx * sens, dy * sens, self.config.walk.speed)

                self.canvas.PanTilt(look_dx * 2.0, 0.0)

            return _wrapper

        if (
            self.config.zoom.mouse is not None and
            self.config.zoom.mouse & code
        ):
            def _wrapper(dx, dy):

                if self.config.zoom.mouse & MOUSE_SWAP_AXIS:
                    dy, dx = dx, dy

                sens = self.config.zoom.sensitivity
                self.canvas.camera.Zoom(dx * sens)

            return _wrapper

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    @property
    @_check_types.do
    def active_event(self) -> _events.GLEvent | _events.GLObjectEvent | None:
        """
        Return the active event.

        :rtype: _events.GLEvent | _events.GLObjectEvent | None
        """

        return self._gl_mouse_event

    @_check_types.do
    def _send_event(self, new_event: _events.GLEvent | _events.GLObjectEvent,
                    qt_event) -> bool:
        """
        Execute the send event operation.

        :param new_event: Value for ``new_event``.
        :type new_event: _events.GLEvent | _events.GLObjectEvent

        :param qt_event: Value for ``qt_event``.
        :type qt_event: UNKNOWN

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

    @_check_types.do
    def _send_capture_lost(self):
        """
        Execute the send capture lost operation.

        Unconditional -- every listener (including any active drag or
        rotation handler, via their own ``gl_capture_lost`` connection)
        is expected to hard-reset itself here regardless of whether
        anything calls ``StopPropagation``.
        """

        event = _events.GLCaptureLostEvent(_events.EVT_GL_CAPTURE_LOST)
        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        self.canvas.gl_capture_lost.emit(event)

        self._is_motion = False

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    @_check_types.do
    def on_left_down(self, evt):
        """
        Handle the left down event.
        """

        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        event = _events.GLEvent(_events.EVT_GL_LEFT_DOWN)
        if self._send_event(event, evt):
            return

        self.canvas.grabMouse()

    @_check_types.do
    def on_left_up(self, evt):
        """
        Handle the left up event.
        """

        refresh = False

        event = _events.GLEvent(_events.EVT_GL_LEFT_UP)

        if self._send_event(event, evt):
            mouse_pos = _qt_pos(evt)
            self._mouse_pos = mouse_pos

            cur_selected = self.canvas.get_selected()
            selected = self._pick_object(mouse_pos, current_selection=cur_selected)

            if not self._is_motion:
                # Read by MainFrame._set_selected: this click is what's about
                # to trigger the selection change below, so the 3D view
                # shouldn't re-center on it -- it's already right where the
                # user clicked.
                self.canvas.mainframe._selection_source_editor = 'editor3d'  # NOQA

                if self._active_cavity_housing is not None:
                    self._active_cavity_housing.clear_cavity_overlay()
                    self._active_cavity_housing = None

                # If the clicked object is a Housing, check whether the click
                # landed on a cavity face and highlight it.  Cavity interaction
                # is intentionally separate from normal object selection: the
                # housing itself gets selected; right-click on it (while a
                # cavity is highlighted) opens the cavity context menu.
                if isinstance(selected, _housing.Housing):
                    view_obj = self._get_view_object(selected)
                    if hasattr(view_obj, 'try_pick_cavity'):
                        cavity = view_obj.try_pick_cavity(
                            int(mouse_pos.x), int(mouse_pos.y))

                        if cavity is not None:
                            self._active_cavity_housing = view_obj
                            selected = cavity.parent

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

        self._mouse_pos = None
        self._is_motion = False

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_left_dclick(self, evt):
        """
        Handle the left dclick event.
        """

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_LEFT_DCLICK)
        if self._send_event(event, evt):
            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view,
                self.canvas.camera, self._get_view_object)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_ACTIVATED)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    @_check_types.do
    def on_middle_up(self, evt):
        """
        Handle the middle up event.
        """

        refresh = False

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_UP)
        if self._send_event(event, evt):
            if not self._is_motion:
                with self.canvas:
                    mouse_pos = _qt_pos(evt)
                    selected = _object_picker.find_object(
                        mouse_pos, self.canvas.objects_in_view,
                        self.canvas.camera, self._get_view_object)

                    if selected:
                        event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_CLICK)
                        event.SetGLObject(selected)
                        self._send_event(event, evt)

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_middle_down(self, evt):
        """
        Handle the middle down event.
        """

        self._is_motion = False

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DOWN)
        self._send_event(event, evt)

        self.canvas.grabMouse()

        self._mouse_pos = _qt_pos(evt)

    @_check_types.do
    def on_middle_dclick(self, evt):
        """
        Handle the middle dclick event.
        """

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view,
                self.canvas.camera, self._get_view_object)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_MIDDLE_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    @_check_types.do
    def on_right_up(self, evt):
        """
        Handle the right up event.
        """

        refresh = False

        event = _events.GLEvent(_events.EVT_GL_RIGHT_UP)
        if self._send_event(event, evt):

            with self.canvas:
                if not self._is_motion:
                    mouse_pos = _qt_pos(evt)

                    selected = self._pick_object(mouse_pos)
                    cur_selected = self.canvas.get_selected()

                    # A fresh pick at this exact position may not resolve
                    # to the same cavity that's actually selected (or to a
                    # cavity at all) -- try_pick_cavity re-derives it
                    # directly, gated on the click having landed on the
                    # housing that has an active cavity highlight in the
                    # first place.
                    cavity = None
                    if (
                        self._active_cavity_housing is not None and
                        self._active_cavity_housing.parent is selected
                    ):
                        view_obj = self._get_view_object(selected)
                        if hasattr(view_obj, 'try_pick_cavity'):
                            cavity = view_obj.try_pick_cavity(
                                int(mouse_pos.x), int(mouse_pos.y))

                    is_cavity_menu_target = cavity is not None and cavity.parent is cur_selected

                    if is_cavity_menu_target or (selected and selected != cur_selected):
                        # Cavity3D.get_context_menu() owns the cavity-aware
                        # menu now, so the event target is the cavity
                        # itself (cavity.parent, the wrapper) rather than
                        # the housing when this was a cavity hit.
                        target = cavity.parent if is_cavity_menu_target else selected

                        event = _events.GLObjectEvent(
                            _events.EVT_GL_OBJECT_RIGHT_CLICK)
                        event.SetGLObject(target)
                        self._send_event(event, evt)
                    else:
                        refresh = True

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_right_down(self, evt):
        """
        Handle the right down event.

        Entering angle mode for the selected object (if this editor's
        rotation handler decides to) is driven entirely by the handler's
        own ``gl_right_down`` connection -- see ``rotation_handler_base.py``.
        This method's only remaining job is emitting the event and
        establishing the mouse grab.
        """

        self._is_motion = False

        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DOWN)
        self._send_event(event, evt)

        self.canvas.grabMouse()

    @_check_types.do
    def on_right_dclick(self, evt):
        """
        Handle the right dclick event.
        """

        mouse_pos = _qt_pos(evt)

        event = _events.GLEvent(_events.EVT_GL_RIGHT_DCLICK)
        if self._send_event(event, evt):

            selected = _object_picker.find_object(
                mouse_pos, self.canvas.objects_in_view,
                self.canvas.camera, self._get_view_object)

            with self.canvas:
                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_DCLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

    @_check_types.do
    def on_mouse_wheel(self, evt):
        """
        Handle the mouse wheel event.
        """

        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0

        if self.config.walk.mouse is not None and self.config.walk.mouse & MOUSE_WHEEL:
            self._orient_to_mouse_on_focal_plane(_qt_pos(evt), delta)

        self._process_mouse(MOUSE_WHEEL)(delta, 0.0)
        self.canvas.repaint()

    @_check_types.do
    def _orient_to_mouse_on_focal_plane(self, mouse_pos: _point.Point, wheel_delta: float) -> None:
        @_check_types.do
        def _norm(values) -> float:
            return math.sqrt(sum(v * v for v in values))

        camera = self.canvas.camera
        target = camera.get_position_on_focal_plane(mouse_pos)
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

        walk_cfg = self.config.walk
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

    @_check_types.do
    def on_mouse_motion(self, evt):
        """
        Handle the mouse motion event.

        Per-button behavior below is always the *default*: any drag or
        rotation handler that wants authority over this motion claims it
        via ``evt.StopPropagation()`` from its own ``gl_mouse_move``
        connection during the ``_send_event`` call just below, which
        this method is already gated on.
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

            with self.canvas:
                if btns & QtCore.Qt.MouseButton.LeftButton:
                    self._is_motion = True
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

        if refresh:
            self.canvas.repaint()

    @_check_types.do
    def on_aux1_up(self, evt):
        """
        Handle the aux 1 up event.
        """

        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(
                    mouse_pos, self.canvas.objects_in_view,
                    self.canvas.camera, self._get_view_object)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    @_check_types.do
    def on_aux1_down(self, evt):
        """
        Handle the aux 1 down event.
        """

        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    @_check_types.do
    def on_aux1_dclick(self, evt):
        """
        Handle the aux 1 dclick event.
        """

        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(
            mouse_pos, self.canvas.objects_in_view,
            self.canvas.camera, self._get_view_object)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX1_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

    @_check_types.do
    def on_aux2_up(self, evt):
        """
        Handle the aux 2 up event.
        """

        if not self._is_motion:
            with self.canvas:
                mouse_pos = _qt_pos(evt)
                selected = _object_picker.find_object(
                    mouse_pos, self.canvas.objects_in_view,
                    self.canvas.camera, self._get_view_object)

                if selected:
                    event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_CLICK)
                    event.SetGLObject(selected)
                    self._send_event(event, evt)

        self.canvas.releaseMouse()

    @_check_types.do
    def on_aux2_down(self, evt):
        """
        Handle the aux 2 down event.
        """

        self._is_motion = False
        self.canvas.grabMouse()
        self._mouse_pos = _qt_pos(evt)

    @_check_types.do
    def on_aux2_dclick(self, evt):
        """
        Handle the aux 2 dclick event.
        """

        mouse_pos = _qt_pos(evt)
        selected = _object_picker.find_object(
            mouse_pos, self.canvas.objects_in_view,
            self.canvas.camera, self._get_view_object)

        with self.canvas:
            if selected:
                event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_AUX2_DCLICK)
                event.SetGLObject(selected)
                self._send_event(event, evt)

    @staticmethod
    def _get_view_object(obj):  # NOQA
        # this function needs to be overridden to return the correct view object
        raise NotImplementedError
