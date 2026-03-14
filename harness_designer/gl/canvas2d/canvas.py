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
        
        # Camera for 2D view
        from . import camera as _camera
        self.camera = _camera.Camera2D(self)
        
        # Grid and snapping
        self._grid_enabled = True
        self._grid_spacing = 10.0  # mm
        self._snap_to_grid = False
        self._angle_lock = False  # Lock movements to orthogonal angles (0, 90, 180, 270)
        self._angle_lock_increment = 90.0  # degrees (90 for orthogonal, 45 for diagonal)
        
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
        return self.camera.x
    
    @camera_x.setter
    def camera_x(self, value):
        """Set camera X position in world coordinates"""
        self.camera.x = float(value)
        
    @property
    def camera_y(self):
        """Get camera Y position in world coordinates"""
        return self.camera.y
    
    @camera_y.setter
    def camera_y(self, value):
        """Set camera Y position in world coordinates"""
        self.camera.y = float(value)
        
    @property
    def zoom(self):
        """Get current zoom level"""
        return self.camera.zoom
    
    @zoom.setter
    def zoom(self, value):
        """Set zoom level (clamped between 0.01 and 100.0)"""
        self.camera.zoom = float(value)
        
    def pan(self, dx, dy):
        """
        Pan the view by delta pixels
        
        Args:
            dx: Change in X (screen coordinates)
            dy: Change in Y (screen coordinates)
        """
        self.camera.pan(dx, dy)
        
    def zoom_at_point(self, screen_x, screen_y, zoom_delta):
        """
        Zoom in/out centered on a specific screen point
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            zoom_delta: Amount to change zoom (positive = zoom in)
        """
        self.camera.zoom_at_point(screen_x, screen_y, zoom_delta)
        
    def screen_to_world(self, screen_x, screen_y):
        """
        Convert screen coordinates to world coordinates
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            
        Returns:
            tuple: (world_x, world_y)
        """
        return self.camera.screen_to_world(screen_x, screen_y)
        
    def world_to_screen(self, world_x, world_y):
        """
        Convert world coordinates to screen coordinates
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            tuple: (screen_x, screen_y)
        """
        return self.camera.world_to_screen(world_x, world_y)
        
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
        
    def apply_angle_lock(self, start_x, start_y, end_x, end_y):
        """
        Apply angle lock to constrain movement to specific angles
        
        Args:
            start_x: Starting X position
            start_y: Starting Y position
            end_x: Target X position
            end_y: Target Y position
            
        Returns:
            tuple: (locked_x, locked_y) - position locked to nearest angle
        """
        if not self._angle_lock:
            return (end_x, end_y)
            
        import math
        
        # Calculate delta
        dx = end_x - start_x
        dy = end_y - start_y
        
        # Calculate angle in degrees
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # Normalize to 0-360
        if angle_deg < 0:
            angle_deg += 360
            
        # Round to nearest increment
        locked_angle_deg = round(angle_deg / self._angle_lock_increment) * self._angle_lock_increment
        locked_angle_rad = math.radians(locked_angle_deg)
        
        # Calculate distance
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Apply locked angle
        locked_x = start_x + distance * math.cos(locked_angle_rad)
        locked_y = start_y + distance * math.sin(locked_angle_rad)
        
        return (locked_x, locked_y)
        
    def toggle_snap_to_grid(self):
        """Toggle snap-to-grid on/off"""
        self._snap_to_grid = not self._snap_to_grid
        return self._snap_to_grid
        
    def toggle_angle_lock(self):
        """Toggle angle lock on/off"""
        self._angle_lock = not self._angle_lock
        return self._angle_lock
        
    def set_angle_lock_increment(self, degrees):
        """
        Set the angle lock increment
        
        Args:
            degrees: Angle increment in degrees (e.g., 90 for orthogonal, 45 for diagonal)
        """
        self._angle_lock_increment = float(degrees)
        
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
    def angle_lock_enabled(self):
        """Check if angle lock is enabled"""
        return self._angle_lock
        
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
        
        # Calculate visible world bounds using camera
        half_width = (width / 2.0) / self.camera.zoom
        half_height = (height / 2.0) / self.camera.zoom
        
        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height
        
        # Orthographic projection
        GL.glOrtho(left, right, bottom, top, -1.0, 1.0)
        
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        
    def _init_gl(self):
        """Initialize OpenGL settings"""
        with self.context:
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
        
        # Use context manager for thread-safe OpenGL access
        with self.context:
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
        pixel_spacing = minor_spacing * self.camera.zoom
        while pixel_spacing < 20:
            minor_spacing *= 10
            pixel_spacing = minor_spacing * self.camera.zoom
        while pixel_spacing > 100:
            minor_spacing /= 10
            pixel_spacing = minor_spacing * self.camera.zoom
            
        # Major grid is 10x minor grid
        major_spacing = minor_spacing * 10
        
        # Calculate visible bounds using camera
        half_width = (width / 2.0) / self.camera.zoom
        half_height = (height / 2.0) / self.camera.zoom
        
        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height
        
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
