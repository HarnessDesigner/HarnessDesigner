from typing import TYPE_CHECKING

import wx
from ... import config as _config
from ...geometry import point as _point
from .. import events as _events

if TYPE_CHECKING:
    from . import canvas as _canvas


# Mouse button configuration
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


class GLEvent(wx.PyEvent):
    """Custom event for 2D GL canvas operations"""

    def __init__(self, event_type):
        wx.PyEvent.__init__(self)
        self.SetEventType(event_type)
        self.world_pos = (0.0, 0.0)
        self.screen_pos = (0, 0)
        self.obj = None
        self.button_states = {}


class MouseHandler2D:
    """
    Handles mouse interactions for the 2D schematic canvas
    """

    def __init__(self, canvas: "_canvas.Canvas"):
        self.canvas = canvas

        self._mouse_pos: _point.Point = None
        self._is_motion = False

        # Mouse state
        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._mouse_down_button = None
        self._drag_obj = None
        self._drag_offset = None
        self._is_panning = False
        self._click_threshold = 3  # pixels

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

    def _get_object_at_point(self, world_pos: _point.Point):
        # Iterate objects in reverse (top to bottom)
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

    def on_left_down(self, evt: wx.MouseEvent):
        """Handle left mouse button down"""
        x, y = evt.GetPosition()

        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        self._is_motion = False
        refresh = False

        # Get world coordinates
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

        # Check for object at position
        selected = self._get_object_at_point(world_pos)
        cur_selected = self.canvas.get_selected()

        if selected is None:
            if cur_selected is not None:
                cur_selected.set_selected(False)
                refresh = True
        else:
            if selected == cur_selected:
                self._drag_obj = selected
                refresh = False
            else:
                if cur_selected is not None:
                    cur_selected.set_selected(False)

                selected.set_selected(True)

                refresh = True

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_left_up(self, evt: wx.MouseEvent):
        """Handle left mouse button up"""
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        refresh = False

        # Get world coordinates
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

        # Check for object at position
        selected = self._get_object_at_point(world_pos)
        cur_selected = self.canvas.get_selected()

        if not self._is_motion and self._drag_obj is not None:
            if selected is not None and selected == cur_selected:
                selected.set_selected(False)
                refresh = True

            if self._drag_obj is not None:
                self._drag_obj = None

        self._is_motion = False

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_left_dclick(self, evt: wx.MouseEvent):
        """Handle left mouse button double-click"""
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        refresh = False

        # Get world coordinates
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

        # Check for object at position
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

            event = _events.GLEvent(_events.wxEVT_GL_OBJECT_ACTIVATED)
            event.obj = selected
            event.world_pos = world_pos
            event.screen_pos = mouse_pos
            wx.PostEvent(self.canvas, event)

        if refresh:
            self.canvas.Refresh(False)

        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):
        """Handle right mouse button down"""
        x, y = evt.GetPosition()

        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):
        """Handle right mouse button up"""
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
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
            self.canvas.Refresh(False)

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_right_dclick(self, evt: wx.MouseEvent):  # NOQA
        """Handle right mouse button double-click"""
        evt.Skip()

    def on_middle_down(self, evt: wx.MouseEvent):
        """Handle middle mouse button down"""
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        if not self.canvas.HasCapture():
            self.canvas.CaptureMouse()

        evt.Skip()

    def on_middle_up(self, evt: wx.MouseEvent):
        """Handle middle mouse button up"""

        x, y = evt.GetPosition()

        mouse_pos = _point.Point(x, y)
        self._mouse_pos = mouse_pos
        self._is_motion = False

        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

    def on_middle_dclick(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_aux1_up(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_aux1_down(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_aux1_dclick(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_aux2_up(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_aux2_down(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_aux2_dclick(self, evt: wx.MouseEvent):  # NOQA
        """Handle middle mouse button double-click"""
        evt.Skip()

    def on_mouse_motion(self, evt: wx.MouseEvent):
        """Handle mouse motion"""
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
                        world_pos = self.canvas.camera.screen_to_world(mouse_pos)

                        if self.canvas.config.grid.snap:
                            world_pos = self.canvas.snap_to_grid(world_pos)

                        if self.canvas.config.angle.lock and self._drag_offset is not None:
                            world_pos = self.canvas.apply_angle_lock(self._drag_offset, world_pos)

                        position = self._drag_obj.obj2d.position
                        position += world_pos - position

                    refresh = True

                if evt.MiddleIsDown():
                    self._is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                    refresh = True

                if evt.RightIsDown():
                    self._is_motion = True
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

    def on_mouse_wheel(self, evt: wx.MouseEvent):
        """Handle mouse wheel for zooming"""
        x, y = evt.GetPosition()
        mouse_pos = _point.Point(x, y)

        rotation = evt.GetWheelRotation()

        # Convert rotation to delta (positive = zoom in, negative = zoom out)
        if rotation > 0:
            delta = 1.0
        else:
            delta = -1.0

        # Zoom centered on cursor position
        self.canvas.camera.zoom_at_point(mouse_pos, delta)

        evt.Skip()

    def _show_canvas_context_menu(self, pos: _point.Point):
        """Show context menu for empty canvas"""
        menu = wx.Menu()

        # Add menu items
        item = menu.Append(wx.ID_ANY, "Reset View")
        self.canvas.Bind(wx.EVT_MENU, self._on_reset_view, id=item.GetId())

        menu.AppendSeparator()

        item = menu.Append(wx.ID_ANY, "Zoom In")
        self.canvas.Bind(wx.EVT_MENU, self._create_zoom_handler(pos, 120), id=item.GetId())

        item = menu.Append(wx.ID_ANY, "Zoom Out")
        self.canvas.Bind(wx.EVT_MENU, self._create_zoom_handler(pos, -120), id=item.GetId())

        item = menu.Append(wx.ID_ANY, "Zoom to Fit")
        self.canvas.Bind(wx.EVT_MENU, self._on_zoom_to_fit, id=item.GetId())

        menu.AppendSeparator()

        # Grid and snap options
        grid_text = "Hide Grid" if self.canvas.grid_enabled else "Show Grid"
        item = menu.Append(wx.ID_ANY, grid_text)
        self.canvas.Bind(wx.EVT_MENU, self._on_toggle_grid, id=item.GetId())

        snap_text = "Disable Snap to Grid" if self.canvas.snap_enabled else "Enable Snap to Grid"
        item = menu.Append(wx.ID_ANY, snap_text)
        self.canvas.Bind(wx.EVT_MENU, self._on_toggle_snap, id=item.GetId())

        angle_text = "Disable Angle Lock" if self.canvas.angle_lock_enabled else "Enable Angle Lock"
        item = menu.Append(wx.ID_ANY, angle_text)
        self.canvas.Bind(wx.EVT_MENU, self._on_toggle_angle_lock, id=item.GetId())

        self.canvas.PopupMenu(menu, pos)
        menu.Destroy()

    def _create_zoom_handler(self, pos: _point.Point, delta: int):
        """Create a zoom handler with captured position"""
        def handler(_):
            self.canvas.camera.zoom_at_point(pos, delta)

        return handler

    def _on_toggle_grid(self, evt: wx.MenuEvent):
        """Toggle grid display"""
        self.canvas.set_grid(not self.canvas.config.grid.enabled)
        evt.Skip()

    def _on_toggle_snap(self, evt: wx.MenuEvent):
        """Toggle snap to grid"""
        self.canvas.set_snap_to_grid(not self.canvas.config.grid.snap)
        # Could show a status message
        evt.Skip()

    def _on_toggle_angle_lock(self, evt: wx.MenuEvent):
        """Toggle angle lock"""
        self.canvas.set_angle_lock(not self.canvas.config.angle.lock)
        # Could show a status message
        evt.Skip()

    def _on_reset_view(self, evt: wx.MenuEvent):
        """Reset view to origin"""
        self.canvas.camera.reset()
        evt.Skip()

    def _on_zoom_to_fit(self, evt: wx.MenuEvent):
        """Zoom to fit all objects"""
        self.canvas.camera.zoom_to_fit(self.canvas.objects)
        evt.Skip()
