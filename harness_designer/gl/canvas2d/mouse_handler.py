# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6.QtWidgets import QMenu

from ... import config as _config
from ...geometry import point as _point
from .. import events as _events
from .. import object_picker as _object_picker
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


class MouseHandler2D(QtCore.QObject):
    """Represent a mouse handler 2D in :mod:`harness_designer.gl.canvas2d.mouse_handler`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`MouseHandler2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        super().__init__()
        self.canvas = canvas

        self._mouse_pos: _point.Point = None
        self._is_motion = False

        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._mouse_down_button = None
        self._drag_obj = None
        self._drag_offset = None
        self._is_panning = False
        self._click_threshold = 3

        # Set on the first on_mouse_motion of a Wire drag (see
        # _wire_drag_session_or_start below), so a whole drag gesture
        # keeps dragging the same segment (and its already-promoted
        # waypoints) rather than re-picking the nearest segment on every
        # motion event. Reset whenever a drag starts/ends.
        self._wire_drag_session = None

        canvas.installEventFilter(self)

    # ------------------------------------------------------------------
    # Signal dispatch helper
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    @_check_types.do
    def eventFilter(self, obj, qt_event):
        """Execute the event filter operation.

        UNKNOWN details are inferred from the callable name and signature.

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_check_types.do
    def _get_object_at_point(self, mouse_pos: _point.Point):
        """Return the object under *mouse_pos* (screen-pixel coordinates).

        Ray-vs-OBB/AABB picking via ``gl.object_picker.find_object``
        (``attr='obj2d'``) against ``self.canvas.camera``'s ``.modelview``/
        ``.projection``/``.viewport`` -- see ``gl.canvas2d.camera.Camera.
        _update_views``. Replaces the previous per-object ``obj2d.hit_test()``
        loop.

        A ``Wire`` without a completed connection at both ends (see
        ``objects/wire.py``'s ``Wire.is_connected``) is excluded from the
        candidate set -- it isn't rendered either (see
        ``gl.canvas2d.canvas.Canvas._render_vbo_objects``), so it
        shouldn't be clickable.

        :param mouse_pos: Screen-pixel mouse position (not world coordinates).
        :type mouse_pos: :class:`_point.Point`
        :returns: The picked object, or ``None``.
        """
        candidates = [
            obj for obj in self.canvas.objects if getattr(obj, 'is_connected', True)]

        return _object_picker.find_object(
            mouse_pos, candidates, self.canvas.camera, self._get_view_object)

    @staticmethod
    def _get_view_object(obj):
        return obj.obj2d

    @_check_types.do
    def _process_mouse(self, code):
        """Execute the process mouse operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param code: Value for ``code``.
        :type code: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        for config, func in (
            (self.canvas.config.pan, self.canvas.Pan),
            (self.canvas.config.zoom, self.canvas.Zoom),
            (self.canvas.config.reset, self.canvas.camera.Reset),
        ):
            if not config.mouse:
                continue

            if config.mouse & code:
                @_check_types.do
                def _wrapper_func(c):
                    """Execute the wrapper func operation.

                    UNKNOWN details are inferred from the callable name and signature.

                    :param c: Value for ``c``.
                    :type c: UNKNOWN
                    :returns: Return value. UNKNOWN details.
                    :rtype: UNKNOWN
                    """
                    @_check_types.do
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

        @_check_types.do
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

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    @_check_types.do
    def on_left_down(self, evt):
        """Handle the left down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        refresh = False

        # Read by MainFrame._set_selected: this click is what's about to
        # trigger the selection change below, so the 2D view shouldn't
        # re-center on it -- it's already right where the user clicked.
        self.canvas.mainframe._selection_source_editor = 'editor2d'  # NOQA

        selected = self._get_object_at_point(mouse_pos)
        cur_selected = self.canvas.get_selected()

        if selected is None:
            if cur_selected is not None:
                cur_selected.set_selected(False)
                unsel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                unsel_event.SetGLObject(cur_selected)
                self._send_event(unsel_event, evt)
                refresh = True
        else:
            if selected == cur_selected:
                self._drag_obj = selected
                self._wire_drag_session = None
            else:
                if cur_selected is not None:
                    cur_selected.set_selected(False)
                    unsel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    unsel_event.SetGLObject(cur_selected)
                    self._send_event(unsel_event, evt)

                selected.set_selected(True)
                sel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                sel_event.SetGLObject(selected)
                self._send_event(sel_event, evt)
                refresh = True

        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DOWN), evt)
        self.canvas.grabMouse()

        if refresh:
            self.canvas.update()

    @_check_types.do
    def on_left_up(self, evt):
        """Handle the left up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        refresh = False

        selected = self._get_object_at_point(mouse_pos)
        cur_selected = self.canvas.get_selected()

        if not self._is_motion and self._drag_obj is not None:
            if selected is not None and selected == cur_selected:
                selected.set_selected(False)
                unsel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                unsel_event.SetGLObject(selected)
                self._send_event(unsel_event, evt)
                refresh = True

            if self._drag_obj is not None:
                self._drag_obj = None

        self._wire_drag_session = None
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_UP), evt)
        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    @_check_types.do
    def on_left_dclick(self, evt):
        """Handle the left dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        refresh = False

        self.canvas.mainframe._selection_source_editor = 'editor2d'  # NOQA

        selected = self._get_object_at_point(mouse_pos)
        cur_selected = self.canvas.get_selected()

        if selected is None:
            if cur_selected is not None:
                cur_selected.set_selected(False)
                refresh = True
        else:
            if cur_selected is not None and cur_selected != selected:
                cur_selected.set_selected(False)
                selected.set_selected(True)
                refresh = True

            event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_ACTIVATED)
            event.SetGLObject(selected)
            self._send_event(event, evt)

        self._send_event(_events.GLEvent(_events.EVT_GL_LEFT_DCLICK), evt)

        if refresh:
            self.canvas.update()

    @_check_types.do
    def on_right_down(self, evt):
        """Handle the right down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DOWN), evt)
        self.canvas.grabMouse()

    @_check_types.do
    def on_right_up(self, evt):
        """Handle the right up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        refresh = False

        if not self._is_motion:
            self.canvas.mainframe._selection_source_editor = 'editor2d'  # NOQA

            selected = self._get_object_at_point(mouse_pos)
            cur_selected = self.canvas.get_selected()

            if selected is not None:
                if cur_selected is None:
                    selected.set_selected(True)
                    sel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                    sel_event.SetGLObject(selected)
                    self._send_event(sel_event, evt)
                    refresh = True

                elif cur_selected != selected:
                    cur_selected.set_selected(False)
                    unsel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_UNSELECTED)
                    unsel_event.SetGLObject(cur_selected)
                    self._send_event(unsel_event, evt)

                    selected.set_selected(True)
                    sel_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_SELECTED)
                    sel_event.SetGLObject(selected)
                    self._send_event(sel_event, evt)
                    refresh = True

                rc_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_RIGHT_CLICK)
                rc_event.SetGLObject(selected)
                self._send_event(rc_event, evt)

                self._show_canvas_context_menu(mouse_pos)

        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_UP), evt)

        if refresh:
            self.canvas.update()

        self.canvas.releaseMouse()

    @_check_types.do
    def on_right_dclick(self, evt):
        """Handle the right dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_RIGHT_DCLICK), evt)

    @_check_types.do
    def on_middle_down(self, evt):
        """Handle the middle down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_DOWN), evt)
        self.canvas.grabMouse()

    @_check_types.do
    def on_middle_up(self, evt):
        """Handle the middle up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._mouse_pos = _qt_pos(evt)
        self._is_motion = False
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_UP), evt)
        self.canvas.releaseMouse()

    @_check_types.do
    def on_middle_dclick(self, evt):
        """Handle the middle dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_MIDDLE_DCLICK), evt)

    @_check_types.do
    def on_aux1_up(self, evt):
        """Handle the aux 1 up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_UP), evt)

    @_check_types.do
    def on_aux1_down(self, evt):
        """Handle the aux 1 down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_DOWN), evt)

    @_check_types.do
    def on_aux1_dclick(self, evt):
        """Handle the aux 1 dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX1_DCLICK), evt)

    @_check_types.do
    def on_aux2_up(self, evt):
        """Handle the aux 2 up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_UP), evt)

    @_check_types.do
    def on_aux2_down(self, evt):
        """Handle the aux 2 down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_DOWN), evt)

    @_check_types.do
    def on_aux2_dclick(self, evt):
        """Handle the aux 2 dclick event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._send_event(_events.GLEvent(_events.EVT_GL_AUX2_DCLICK), evt)

    @_check_types.do
    def on_mouse_motion(self, evt):
        """Handle the mouse motion event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
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

                    if self._drag_obj is None:
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                    else:
                        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

                        if self.canvas.config.grid.snap:
                            world_pos = self.canvas.snap_to_grid(world_pos)

                        if self.canvas.config.angle.lock and self._drag_offset is not None:
                            world_pos = self.canvas.apply_angle_lock(self._drag_offset, world_pos)

                        obj2d = self._drag_obj.obj2d
                        if hasattr(obj2d, 'begin_segment_drag'):
                            # A wire's own position is just its start
                            # endpoint -- dragging that would stretch/
                            # re-angle it rather than move a section of
                            # its path, so it gets its own interaction
                            # (see objects2d/wire.py's begin_segment_drag/
                            # update_segment_drag) instead of the generic
                            # "set .position" path below.
                            if self._wire_drag_session is None:
                                self._wire_drag_session = obj2d.begin_segment_drag(world_pos)

                            if self._wire_drag_session is not None:
                                obj2d.update_segment_drag(self._wire_drag_session, world_pos)
                        else:
                            position = obj2d.position
                            position += world_pos - position

                        drag_event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_DRAG)
                        drag_event.SetGLObject(self._drag_obj)
                        self._send_event(drag_event, evt)

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

    @_check_types.do
    def on_mouse_wheel(self, evt):
        """Handle the mouse wheel event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mouse_pos = _qt_pos(evt)
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self.canvas.camera.zoom_at_point(mouse_pos, delta)
        self.canvas.update()

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    @_check_types.do
    def _show_canvas_context_menu(self, pos: _point.Point):
        """Show the canvas context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :param pos: Value for ``pos``.
        :type pos: :class:`_point.Point`
        """
        menu = QMenu(self.canvas)

        act = menu.addAction("Reset View")
        act.triggered.connect(self._on_reset_view)

        menu.addSeparator()

        act = menu.addAction("Zoom In")
        act.triggered.connect(lambda: self.canvas.camera.zoom_at_point(pos, 120))

        act = menu.addAction("Zoom Out")
        act.triggered.connect(lambda: self.canvas.camera.zoom_at_point(pos, -120))

        act = menu.addAction("Zoom to Fit")
        act.triggered.connect(self._on_zoom_to_fit)

        menu.addSeparator()

        grid_text = "Hide Grid" if self.canvas.grid_enabled else "Show Grid"
        act = menu.addAction(grid_text)
        act.triggered.connect(self._on_toggle_grid)

        snap_text = "Disable Snap to Grid" if self.canvas.snap_enabled else "Enable Snap to Grid"
        act = menu.addAction(snap_text)
        act.triggered.connect(self._on_toggle_snap)

        angle_text = "Disable Angle Lock" if self.canvas.angle_lock_enabled else "Enable Angle Lock"
        act = menu.addAction(angle_text)
        act.triggered.connect(self._on_toggle_angle_lock)

        from PySide6.QtCore import QPoint
        menu.exec(self.canvas.mapToGlobal(QPoint(int(pos.x), int(pos.y))))

    @_check_types.do
    def _on_toggle_grid(self):
        """Handle the toggle grid event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.canvas.set_grid(not self.canvas.config.grid.enabled)

    @_check_types.do
    def _on_toggle_snap(self):
        """Handle the toggle snap event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.canvas.set_snap_to_grid(not self.canvas.config.grid.snap)

    @_check_types.do
    def _on_toggle_angle_lock(self):
        """Handle the toggle angle lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.canvas.set_angle_lock(not self.canvas.config.angle.lock)

    @_check_types.do
    def _on_reset_view(self):
        """Handle the reset view event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.canvas.camera.reset()

    @_check_types.do
    def _on_zoom_to_fit(self):
        """Handle the zoom to fit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.canvas.camera.zoom_to_fit(self.canvas.objects)
