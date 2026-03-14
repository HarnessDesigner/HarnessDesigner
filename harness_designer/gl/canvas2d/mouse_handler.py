"""
2D Mouse Handler for Schematic Editor

Handles all mouse interactions:
- Left click: Select objects
- Left drag: Drag objects or pan
- Right click: Context menu
- Middle/Right drag: Pan
- Mouse wheel: Zoom
- Double click: Activate/edit objects
"""

import wx
from ... import config as _config


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


# Custom event types for 2D canvas
wxEVT_GL2D_OBJECT_SELECTED = wx.NewEventType()
EVT_GL2D_OBJECT_SELECTED = wx.PyEventBinder(wxEVT_GL2D_OBJECT_SELECTED, 0)

wxEVT_GL2D_OBJECT_UNSELECTED = wx.NewEventType()
EVT_GL2D_OBJECT_UNSELECTED = wx.PyEventBinder(wxEVT_GL2D_OBJECT_UNSELECTED, 0)

wxEVT_GL2D_OBJECT_ACTIVATED = wx.NewEventType()
EVT_GL2D_OBJECT_ACTIVATED = wx.PyEventBinder(wxEVT_GL2D_OBJECT_ACTIVATED, 0)

wxEVT_GL2D_OBJECT_RIGHT_CLICK = wx.NewEventType()
EVT_GL2D_OBJECT_RIGHT_CLICK = wx.PyEventBinder(wxEVT_GL2D_OBJECT_RIGHT_CLICK, 0)

wxEVT_GL2D_OBJECT_DRAG = wx.NewEventType()
EVT_GL2D_OBJECT_DRAG = wx.PyEventBinder(wxEVT_GL2D_OBJECT_DRAG, 0)


class GLEvent2D(wx.PyEvent):
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
    
    def __init__(self, canvas):
        self.canvas = canvas
        
        # Mouse state
        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._mouse_down_button = None
        self._dragging_object = None
        self._drag_offset = None
        self._is_panning = False
        self._click_threshold = 3  # pixels
        
        # Bind mouse events
        canvas.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        canvas.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        canvas.Bind(wx.EVT_LEFT_DCLICK, self._on_left_dclick)
        
        canvas.Bind(wx.EVT_RIGHT_DOWN, self._on_right_down)
        canvas.Bind(wx.EVT_RIGHT_UP, self._on_right_up)
        canvas.Bind(wx.EVT_RIGHT_DCLICK, self._on_right_dclick)
        
        canvas.Bind(wx.EVT_MIDDLE_DOWN, self._on_middle_down)
        canvas.Bind(wx.EVT_MIDDLE_UP, self._on_middle_up)
        
        canvas.Bind(wx.EVT_MOTION, self._on_motion)
        canvas.Bind(wx.EVT_MOUSEWHEEL, self._on_mousewheel)
        canvas.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._on_capture_lost)
        
    def _get_object_at_point(self, world_x, world_y):
        """
        Find object at given world coordinates
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            Object at point or None
        """
        # Iterate objects in reverse (top to bottom)
        for obj in reversed(self.canvas.objects):
            if hasattr(obj, 'obj2d') and hasattr(obj.obj2d, 'hit_test'):
                if obj.obj2d.hit_test(world_x, world_y):
                    return obj
        return None
        
    def _on_left_down(self, event):
        """Handle left mouse button down"""
        pos = event.GetPosition()
        self._mouse_down_pos = pos
        self._last_mouse_pos = pos
        self._mouse_down_button = MOUSE_LEFT
        
        # Get world coordinates
        world_pos = self.canvas.screen_to_world(pos.x, pos.y)
        
        # Check for object at position
        obj = self._get_object_at_point(world_pos[0], world_pos[1])
        
        if obj is not None:
            # Object clicked - prepare for potential drag
            self._dragging_object = obj
            self._drag_offset = world_pos
            
            # Select object
            self.canvas.set_selected(obj)
            
            # Send selection event
            evt = GLEvent2D(wxEVT_GL2D_OBJECT_SELECTED)
            evt.obj = obj
            evt.world_pos = world_pos
            evt.screen_pos = (pos.x, pos.y)
            wx.PostEvent(self.canvas, evt)
        else:
            # No object - deselect
            if self.canvas.get_selected() is not None:
                old_obj = self.canvas.get_selected()
                self.canvas.set_selected(None)
                
                # Send unselection event
                evt = GLEvent2D(wxEVT_GL2D_OBJECT_UNSELECTED)
                evt.obj = old_obj
                evt.world_pos = world_pos
                evt.screen_pos = (pos.x, pos.y)
                wx.PostEvent(self.canvas, evt)
                
        self.canvas.CaptureMouse()
        event.Skip()
        
    def _on_left_up(self, event):
        """Handle left mouse button up"""
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()
            
        pos = event.GetPosition()
        
        # Check if this was a click (not a drag)
        if self._mouse_down_pos is not None:
            dx = abs(pos.x - self._mouse_down_pos.x)
            dy = abs(pos.y - self._mouse_down_pos.y)
            was_click = dx < self._click_threshold and dy < self._click_threshold
            
            if was_click and self._dragging_object is None:
                # This was a click on empty space - already handled in _on_left_down
                pass
                
        # Reset drag state
        self._dragging_object = None
        self._drag_offset = None
        self._mouse_down_pos = None
        self._mouse_down_button = None
        
        event.Skip()
        
    def _on_left_dclick(self, event):
        """Handle left mouse button double-click"""
        pos = event.GetPosition()
        world_pos = self.canvas.screen_to_world(pos.x, pos.y)
        
        # Find object at position
        obj = self._get_object_at_point(world_pos[0], world_pos[1])
        
        if obj is not None:
            # Send activation event
            evt = GLEvent2D(wxEVT_GL2D_OBJECT_ACTIVATED)
            evt.obj = obj
            evt.world_pos = world_pos
            evt.screen_pos = (pos.x, pos.y)
            wx.PostEvent(self.canvas, evt)
            
        event.Skip()
        
    def _on_right_down(self, event):
        """Handle right mouse button down"""
        pos = event.GetPosition()
        self._mouse_down_pos = pos
        self._last_mouse_pos = pos
        self._mouse_down_button = MOUSE_RIGHT
        self._is_panning = True
        
        self.canvas.CaptureMouse()
        event.Skip()
        
    def _on_right_up(self, event):
        """Handle right mouse button up"""
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()
            
        pos = event.GetPosition()
        
        # Check if this was a click (not a pan)
        if self._mouse_down_pos is not None:
            dx = abs(pos.x - self._mouse_down_pos.x)
            dy = abs(pos.y - self._mouse_down_pos.y)
            was_click = dx < self._click_threshold and dy < self._click_threshold
            
            if was_click:
                # Show context menu
                world_pos = self.canvas.screen_to_world(pos.x, pos.y)
                obj = self._get_object_at_point(world_pos[0], world_pos[1])
                
                if obj is not None:
                    # Send right-click event
                    evt = GLEvent2D(wxEVT_GL2D_OBJECT_RIGHT_CLICK)
                    evt.obj = obj
                    evt.world_pos = world_pos
                    evt.screen_pos = (pos.x, pos.y)
                    wx.PostEvent(self.canvas, evt)
                else:
                    # Right-click on empty space - show canvas context menu
                    self._show_canvas_context_menu(pos)
                    
        self._is_panning = False
        self._mouse_down_pos = None
        self._mouse_down_button = None
        
        event.Skip()
        
    def _on_right_dclick(self, event):
        """Handle right mouse button double-click"""
        event.Skip()
        
    def _on_middle_down(self, event):
        """Handle middle mouse button down"""
        pos = event.GetPosition()
        self._mouse_down_pos = pos
        self._last_mouse_pos = pos
        self._mouse_down_button = MOUSE_MIDDLE
        self._is_panning = True
        
        self.canvas.CaptureMouse()
        event.Skip()
        
    def _on_middle_up(self, event):
        """Handle middle mouse button up"""
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()
            
        self._is_panning = False
        self._mouse_down_pos = None
        self._mouse_down_button = None
        
        event.Skip()
        
    def _on_motion(self, event):
        """Handle mouse motion"""
        pos = event.GetPosition()
        
        if self._last_mouse_pos is None:
            self._last_mouse_pos = pos
            return
            
        dx = pos.x - self._last_mouse_pos.x
        dy = pos.y - self._last_mouse_pos.y
        
        if self._is_panning:
            # Pan the view
            self.canvas.pan(dx, dy)
        elif self._dragging_object is not None and event.Dragging() and event.LeftIsDown():
            # Drag object
            world_pos = self.canvas.screen_to_world(pos.x, pos.y)
            
            # Apply snap to grid if enabled
            if self.canvas.snap_enabled:
                world_pos = self.canvas.snap_to_grid(world_pos[0], world_pos[1])
                
            # Apply angle lock if enabled and we have a drag offset
            if self.canvas.angle_lock_enabled and self._drag_offset is not None:
                world_pos = self.canvas.apply_angle_lock(
                    self._drag_offset[0], self._drag_offset[1],
                    world_pos[0], world_pos[1]
                )
            
            # Send drag event
            evt = GLEvent2D(wxEVT_GL2D_OBJECT_DRAG)
            evt.obj = self._dragging_object
            evt.world_pos = world_pos
            evt.screen_pos = (pos.x, pos.y)
            wx.PostEvent(self.canvas, evt)
            
            # Update object position (if it has a position property)
            if hasattr(self._dragging_object, 'obj2d') and hasattr(self._dragging_object.obj2d, 'move_to'):
                self._dragging_object.obj2d.move_to(world_pos[0], world_pos[1])
                self.canvas.Refresh()
        else:
            # Update hover state
            world_pos = self.canvas.screen_to_world(pos.x, pos.y)
            obj = self._get_object_at_point(world_pos[0], world_pos[1])
            
            if obj != self.canvas._hovered:
                self.canvas._hovered = obj
                # Could trigger hover events here
                
        self._last_mouse_pos = pos
        event.Skip()
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel for zooming"""
        pos = event.GetPosition()
        rotation = event.GetWheelRotation()
        
        # Zoom centered on cursor position
        self.canvas.zoom_at_point(pos.x, pos.y, rotation)
        
        event.Skip()
        
    def _on_capture_lost(self, event):
        """Handle lost mouse capture"""
        self._mouse_down_pos = None
        self._mouse_down_button = None
        self._dragging_object = None
        self._drag_offset = None
        self._is_panning = False
        
    def _show_canvas_context_menu(self, pos):
        """Show context menu for empty canvas"""
        menu = wx.Menu()
        
        # Add menu items
        item = menu.Append(wx.ID_ANY, "Reset View")
        self.canvas.Bind(wx.EVT_MENU, self._on_reset_view, id=item.GetId())
        
        menu.AppendSeparator()
        
        item = menu.Append(wx.ID_ANY, "Zoom In")
        self.canvas.Bind(wx.EVT_MENU, self._create_zoom_handler(pos.x, pos.y, 120), id=item.GetId())
        
        item = menu.Append(wx.ID_ANY, "Zoom Out")
        self.canvas.Bind(wx.EVT_MENU, self._create_zoom_handler(pos.x, pos.y, -120), id=item.GetId())
        
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
        
    def _create_zoom_handler(self, x, y, delta):
        """Create a zoom handler with captured position"""
        def handler(event):
            self.canvas.zoom_at_point(x, y, delta)
        return handler
        
    def _on_toggle_grid(self, event):
        """Toggle grid display"""
        self.canvas.toggle_grid_display()
        
    def _on_toggle_snap(self, event):
        """Toggle snap to grid"""
        enabled = self.canvas.toggle_snap_to_grid()
        # Could show a status message
        
    def _on_toggle_angle_lock(self, event):
        """Toggle angle lock"""
        enabled = self.canvas.toggle_angle_lock()
        # Could show a status message
        
    def _on_reset_view(self, event):
        """Reset view to origin"""
        self.canvas.camera.reset()
        
    def _on_zoom_to_fit(self, event):
        """Zoom to fit all objects"""
        self.canvas.camera.zoom_to_fit(self.canvas.objects)
