"""
2D Schematic Editor Canvas using OpenGL

This canvas provides a 2D orthographic view for schematic editing of wire harnesses.
It handles:
- 2D OpenGL rendering with orthographic projection
- Pan and zoom operations
- Mouse interactions (select, drag, click)
- Object picking and selection
- Coordinate transformations between screen and world space
"""

import wx
import numpy as np
from wx import glcanvas
from wx import aui
from OpenGL import GL
from OpenGL import GLU

from .. import context as _context
from ... import config as _config
from ... import debug as _debug
from ...geometry import point as _point


class Canvas2D(glcanvas.GLCanvas):
    """
    2D OpenGL Canvas for Schematic Editor
    
    Provides orthographic 2D view with:
    - 1:1 mm mapping (same as 3D canvas)
    - Pan and zoom capabilities
    - Object selection and dragging
    - Point-based coordinate system
    - Snap-to-grid functionality
    """
    
    def __init__(self, parent, config: _config.Config.editor3d, size=wx.DefaultSize, pos=wx.DefaultPosition):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, pos=pos)
        
        try:
            self.mainframe = aui.AuiManager.GetManager(parent).GetManagedWindow()
        except AttributeError:
            self.mainframe = parent
            
        self.config = config
        self._init = False
        self.context = _context.GLContext(self)
        
        # Camera/view properties for 2D
        self._camera_x = 0.0  # Camera center X position (world coords)
        self._camera_y = 0.0  # Camera center Y position (world coords)
        self._zoom = 1.0  # Zoom level (1.0 = 1 pixel = 1 mm)
        
        # Grid and snapping
        self._grid_enabled = True
        self._grid_spacing = 10.0  # mm
        self._snap_to_grid = False
        
        # Mouse state
        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._is_panning = False
        self._is_dragging = False
        
        # Objects and selection
        self._objects = []
        self._selected = None
        self._hovered = None
        
        # Reference counting for deferred refresh
        self._ref_count = 0
        
        self.size = None
        
        # Event bindings
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        
        # Mouse handlers
        from . import mouse_handler as _mouse_handler
        self._mouse_handler = _mouse_handler.MouseHandler2D(self)
        
        font = self.GetFont()
        font.SetPointSize(12)
        self.SetFont(font)
        
    @property
    def camera_x(self):
        """Get camera X position in world coordinates"""
        return self._camera_x
    
    @camera_x.setter
    def camera_x(self, value):
        """Set camera X position in world coordinates"""
        self._camera_x = float(value)
        self.Refresh()
        
    @property
    def camera_y(self):
        """Get camera Y position in world coordinates"""
        return self._camera_y
    
    @camera_y.setter
    def camera_y(self, value):
        """Set camera Y position in world coordinates"""
        self._camera_y = float(value)
        self.Refresh()
        
    @property
    def zoom(self):
        """Get current zoom level"""
        return self._zoom
    
    @zoom.setter
    def zoom(self, value):
        """Set zoom level (clamped between 0.01 and 100.0)"""
        self._zoom = max(0.01, min(100.0, float(value)))
        self.Refresh()
        
    def pan(self, dx, dy):
        """
        Pan the view by delta pixels
        
        Args:
            dx: Change in X (screen coordinates)
            dy: Change in Y (screen coordinates)
        """
        # Convert screen delta to world delta (accounting for zoom)
        world_dx = dx / self._zoom
        world_dy = -dy / self._zoom  # Invert Y for screen coordinates
        
        self._camera_x -= world_dx
        self._camera_y -= world_dy
        self.Refresh()
        
    def zoom_at_point(self, screen_x, screen_y, zoom_delta):
        """
        Zoom in/out centered on a specific screen point
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            zoom_delta: Amount to change zoom (positive = zoom in)
        """
        # Get world position before zoom
        world_pos_before = self.screen_to_world(screen_x, screen_y)
        
        # Apply zoom
        zoom_factor = 1.1 if zoom_delta > 0 else 0.9
        self._zoom = max(0.01, min(100.0, self._zoom * zoom_factor))
        
        # Get world position after zoom
        world_pos_after = self.screen_to_world(screen_x, screen_y)
        
        # Adjust camera to keep the point under cursor
        self._camera_x += world_pos_before[0] - world_pos_after[0]
        self._camera_y += world_pos_before[1] - world_pos_after[1]
        
        self.Refresh()
        
    def screen_to_world(self, screen_x, screen_y):
        """
        Convert screen coordinates to world coordinates
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            
        Returns:
            tuple: (world_x, world_y)
        """
        if self.size is None:
            return (0.0, 0.0)
            
        width, height = self.size
        
        # Screen center
        center_x = width / 2.0
        center_y = height / 2.0
        
        # Offset from center
        offset_x = screen_x - center_x
        offset_y = center_y - screen_y  # Invert Y
        
        # World coordinates
        world_x = self._camera_x + (offset_x / self._zoom)
        world_y = self._camera_y + (offset_y / self._zoom)
        
        return (world_x, world_y)
        
    def world_to_screen(self, world_x, world_y):
        """
        Convert world coordinates to screen coordinates
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            tuple: (screen_x, screen_y)
        """
        if self.size is None:
            return (0, 0)
            
        width, height = self.size
        
        # Offset from camera
        offset_x = (world_x - self._camera_x) * self._zoom
        offset_y = (world_y - self._camera_y) * self._zoom
        
        # Screen coordinates
        screen_x = (width / 2.0) + offset_x
        screen_y = (height / 2.0) - offset_y  # Invert Y
        
        return (int(screen_x), int(screen_y))
        
    def snap_to_grid(self, world_x, world_y):
        """
        Snap world coordinates to grid
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            tuple: (snapped_world_x, snapped_world_y)
        """
        if not self._snap_to_grid:
            return (world_x, world_y)
            
        spacing = self._grid_spacing
        snapped_x = round(world_x / spacing) * spacing
        snapped_y = round(world_y / spacing) * spacing
        
        return (snapped_x, snapped_y)
        
    def toggle_snap_to_grid(self):
        """Toggle snap-to-grid on/off"""
        self._snap_to_grid = not self._snap_to_grid
        return self._snap_to_grid
        
    def toggle_grid_display(self):
        """Toggle grid display on/off"""
        self._grid_enabled = not self._grid_enabled
        self.Refresh()
        return self._grid_enabled
        
    @property
    def snap_enabled(self):
        """Check if snap-to-grid is enabled"""
        return self._snap_to_grid
        
    @property
    def grid_enabled(self):
        """Check if grid display is enabled"""
        return self._grid_enabled
        
    def set_selected(self, obj):
        """Set the currently selected object"""
        if self._selected == obj:
            return
            
        if self._selected is not None:
            if hasattr(self._selected, 'obj2d'):
                self._selected.obj2d.set_selected(False)
                
        self._selected = obj
        
        if self._selected is not None:
            if hasattr(self._selected, 'obj2d'):
                self._selected.obj2d.set_selected(True)
                
        self.Refresh()
        
    def get_selected(self):
        """Get the currently selected object"""
        return self._selected
        
    def add_object(self, obj):
        """Add an object to the canvas"""
        if obj not in self._objects:
            self._objects.append(obj)
            self.Refresh()
            
    def remove_object(self, obj):
        """Remove an object from the canvas"""
        try:
            self._objects.remove(obj)
            if self._selected == obj:
                self._selected = None
            if self._hovered == obj:
                self._hovered = None
            self.Refresh()
        except ValueError:
            pass
            
    @property
    def objects(self):
        """Get list of all objects"""
        return self._objects
        
    def __enter__(self):
        """Context manager entry - increment reference count"""
        self._ref_count += 1
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - decrement reference count"""
        self._ref_count -= 1
        
    def Refresh(self, *args, **kwargs):
        """Refresh the canvas (respects reference counting)"""
        if self._ref_count:
            return
        glcanvas.GLCanvas.Refresh(self, *args, **kwargs)
        
    def _on_erase_background(self, event):
        """Prevent flicker by not erasing background"""
        pass
        
    def _on_size(self, event):
        """Handle resize events"""
        size = self.GetClientSize()
        self.size = (size.width, size.height)
        
        if self._init:
            self.context.SetCurrent(self)
            GL.glViewport(0, 0, size.width, size.height)
            self._setup_projection()
            
        event.Skip()
        
    def _setup_projection(self):
        """Setup orthographic projection for 2D rendering"""
        if self.size is None:
            return
            
        width, height = self.size
        if width == 0 or height == 0:
            return
            
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        
        # Calculate visible world bounds
        half_width = (width / 2.0) / self._zoom
        half_height = (height / 2.0) / self._zoom
        
        left = self._camera_x - half_width
        right = self._camera_x + half_width
        bottom = self._camera_y - half_height
        top = self._camera_y + half_height
        
        # Orthographic projection
        GL.glOrtho(left, right, bottom, top, -1.0, 1.0)
        
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        
    def _init_gl(self):
        """Initialize OpenGL settings"""
        self.context.SetCurrent(self)
        
        # Basic OpenGL setup
        GL.glClearColor(0.15, 0.15, 0.15, 1.0)  # Dark gray background
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
        
        # Disable depth test for 2D
        GL.glDisable(GL.GL_DEPTH_TEST)
        
        # Setup projection
        if self.size:
            GL.glViewport(0, 0, self.size[0], self.size[1])
        self._setup_projection()
        
        self._init = True
        
    def _on_paint(self, event):
        """Handle paint events - render the scene"""
        if not self._init:
            self._init_gl()
            
        self.context.SetCurrent(self)
        
        # Clear the screen
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        
        # Setup projection (in case zoom/pan changed)
        self._setup_projection()
        
        # Render grid
        self._render_grid()
        
        # Render all objects
        for obj in self._objects:
            if hasattr(obj, 'obj2d') and hasattr(obj.obj2d, 'render_gl'):
                obj.obj2d.render_gl()
                
        # Render selection highlight
        if self._selected is not None:
            if hasattr(self._selected, 'obj2d') and hasattr(self._selected.obj2d, 'render_selection'):
                self._selected.obj2d.render_selection()
                
        # Swap buffers
        self.SwapBuffers()
        
    def _render_grid(self):
        """Render background grid with major and minor lines that adapt to zoom level"""
        if not self._grid_enabled or self.size is None:
            return
            
        width, height = self.size
        
        # Calculate grid spacing based on zoom
        # Grid should be between 20-100 pixels apart for minor lines
        base_spacing = 10.0  # mm - base minor grid spacing
        minor_spacing = base_spacing
        
        # Adjust spacing for zoom to keep grid visible but not too dense
        pixel_spacing = minor_spacing * self._zoom
        while pixel_spacing < 20:
            minor_spacing *= 10
            pixel_spacing = minor_spacing * self._zoom
        while pixel_spacing > 100:
            minor_spacing /= 10
            pixel_spacing = minor_spacing * self._zoom
            
        # Major grid is 10x minor grid
        major_spacing = minor_spacing * 10
        
        # Calculate visible bounds
        half_width = (width / 2.0) / self._zoom
        half_height = (height / 2.0) / self._zoom
        
        left = self._camera_x - half_width
        right = self._camera_x + half_width
        bottom = self._camera_y - half_height
        top = self._camera_y + half_height
        
        # Round to grid
        minor_start_x = int(left / minor_spacing) * minor_spacing
        minor_start_y = int(bottom / minor_spacing) * minor_spacing
        major_start_x = int(left / major_spacing) * major_spacing
        major_start_y = int(bottom / major_spacing) * major_spacing
        
        # Draw minor grid lines (dashed, thinner, lighter)
        GL.glEnable(GL.GL_LINE_STIPPLE)
        GL.glLineStipple(1, 0xAAAA)  # Dotted pattern
        GL.glColor4f(0.18, 0.18, 0.18, 1.0)  # Slightly lighter than background
        GL.glLineWidth(1.0)
        
        GL.glBegin(GL.GL_LINES)
        
        # Minor vertical lines
        x = minor_start_x
        while x <= right:
            # Skip if this is a major grid line
            if abs(x % major_spacing) > 0.01:
                GL.glVertex2f(x, bottom)
                GL.glVertex2f(x, top)
            x += minor_spacing
            
        # Minor horizontal lines
        y = minor_start_y
        while y <= top:
            # Skip if this is a major grid line
            if abs(y % major_spacing) > 0.01:
                GL.glVertex2f(left, y)
                GL.glVertex2f(right, y)
            y += minor_spacing
            
        GL.glEnd()
        GL.glDisable(GL.GL_LINE_STIPPLE)
        
        # Draw major grid lines (solid, thicker, more visible)
        GL.glColor4f(0.25, 0.25, 0.25, 1.0)  # More visible than minor
        GL.glLineWidth(1.5)
        
        GL.glBegin(GL.GL_LINES)
        
        # Major vertical lines
        x = major_start_x
        while x <= right:
            # Don't draw major line at origin (will be drawn separately)
            if abs(x) > 0.01:
                GL.glVertex2f(x, bottom)
                GL.glVertex2f(x, top)
            x += major_spacing
            
        # Major horizontal lines
        y = major_start_y
        while y <= top:
            # Don't draw major line at origin (will be drawn separately)
            if abs(y) > 0.01:
                GL.glVertex2f(left, y)
                GL.glVertex2f(right, y)
            y += major_spacing
            
        GL.glEnd()
        
        # Draw axes (origin) with distinct color
        GL.glColor4f(0.35, 0.35, 0.35, 1.0)  # Brighter for axes
        GL.glLineWidth(2.0)
        
        GL.glBegin(GL.GL_LINES)
        # X axis
        if bottom <= 0 <= top:
            GL.glVertex2f(left, 0.0)
            GL.glVertex2f(right, 0.0)
        # Y axis
        if left <= 0 <= right:
            GL.glVertex2f(0.0, bottom)
            GL.glVertex2f(0.0, top)
        GL.glEnd()
