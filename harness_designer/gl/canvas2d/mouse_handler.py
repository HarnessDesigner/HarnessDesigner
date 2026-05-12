# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6.QtWidgets import QMenu

from ... import config as _config
from ...geometry import point as _point
from .. import events as _events


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


def _qt_pos(qt_event) -> _point.Point:
    p = qt_event.position().toPoint()
    return _point.Point(p.x(), p.y())


class MouseHandler2D(QtCore.QObject):

    def __init__(self, canvas: "_canvas.Canvas"):
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

        canvas.installEventFilter(self)

    # ------------------------------------------------------------------
    # Qt event filter dispatcher
    # ------------------------------------------------------------------

    def eventFilter(self, obj, qt_event):
        if obj is not self.canvas:
            return False

        t = qt_event.type()

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

    def _get_object_at_point(self, world_pos: _point.Point):
        for obj in reversed(self.canvas.objects):
            if obj.obj2d.hit_test(world_pos):
                return obj
        return None

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

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def on_left_down(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        refresh = False

        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

        selected = self._get_object_at_point(world_pos)
        cur_selected = self.canvas.get_selected()

        if selected is None:
            if cur_selected is not None:
                cur_selected.set_selected(False)
                refresh = True
        else:
            if selected == cur_selected:
                self._drag_obj = selected
            else:
                if cur_selected is not None:
                    cur_selected.set_selected(False)

                selected.set_selected(True)
                refresh = True

        self.canvas.grabMouse()

        if refresh:
            self.canvas.update()

    def on_left_up(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        refresh = False

        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        selected = self._get_object_at_point(world_pos)
        cur_selected = self.canvas.get_selected()

        if not self._is_motion and self._drag_obj is not None:
            if selected is not None and selected == cur_selected:
                selected.set_selected(False)
                refresh = True

            if self._drag_obj is not None:
                self._drag_obj = None

        self._is_motion = False

        self.canvas.releaseMouse()

        if refresh:
            self.canvas.update()

    def on_left_dclick(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        refresh = False

        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        selected = self._get_object_at_point(world_pos)
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

            # Emit the activated signal on the canvas.
            event = _events.GLObjectEvent(_events.EVT_GL_OBJECT_ACTIVATED)
            event.SetGLObject(selected)
            event.SetPosition(mouse_pos)
            event.SetWorldPosition(world_pos)
            self.canvas.gl_object_activated.emit(event)

        if refresh:
            self.canvas.update()

    def on_right_down(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        self.canvas.grabMouse()

    def on_right_up(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        refresh = False

        if not self._is_motion:
            world_pos = self.canvas.camera.screen_to_world(mouse_pos)

            selected = self._get_object_at_point(world_pos)
            cur_selected = self.canvas.get_selected()

            if selected is not None:
                if cur_selected is None:
                    selected.set_selected(True)
                    refresh = True

                elif cur_selected != selected:
                    cur_selected.set_selected(False)
                    selected.set_selected(True)
                    refresh = True

                self._show_canvas_context_menu(mouse_pos)

        self._is_motion = False

        if refresh:
            self.canvas.update()

        self.canvas.releaseMouse()

    def on_right_dclick(self, evt):
        pass

    def on_middle_down(self, evt):
        mouse_pos = _qt_pos(evt)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        self.canvas.grabMouse()

    def on_middle_up(self, evt):
        self._mouse_pos = _qt_pos(evt)
        self._is_motion = False
        self.canvas.releaseMouse()

    def on_middle_dclick(self, evt):
        pass

    def on_aux1_up(self, evt):
        pass

    def on_aux1_down(self, evt):
        pass

    def on_aux1_dclick(self, evt):
        pass

    def on_aux2_up(self, evt):
        pass

    def on_aux2_down(self, evt):
        pass

    def on_aux2_dclick(self, evt):
        pass

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

                    if self._drag_obj is None:
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])
                    else:
                        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

                        if self.canvas.config.grid.snap:
                            world_pos = self.canvas.snap_to_grid(world_pos)

                        if self.canvas.config.angle.lock and self._drag_offset is not None:
                            world_pos = self.canvas.apply_angle_lock(self._drag_offset, world_pos)

                        position = self._drag_obj.obj2d.position
                        position += world_pos - position

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

    def on_mouse_wheel(self, evt):
        mouse_pos = _qt_pos(evt)
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self.canvas.camera.zoom_at_point(mouse_pos, delta)
        self.canvas.update()

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_canvas_context_menu(self, pos: _point.Point):
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

    def _on_toggle_grid(self):
        self.canvas.set_grid(not self.canvas.config.grid.enabled)

    def _on_toggle_snap(self):
        self.canvas.set_snap_to_grid(not self.canvas.config.grid.snap)

    def _on_toggle_angle_lock(self):
        self.canvas.set_angle_lock(not self.canvas.config.angle.lock)

    def _on_reset_view(self):
        self.canvas.camera.reset()

    def _on_zoom_to_fit(self):
        self.canvas.camera.zoom_to_fit(self.canvas.objects)
