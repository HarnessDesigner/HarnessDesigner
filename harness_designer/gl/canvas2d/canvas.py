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
import math
from wx import glcanvas
from wx import aui
from OpenGL import GL

from .. import context as _context
from ... import config as _config
# from ... import debug as _debug
from ...geometry import point as _point
from . import grid as _grid


MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS


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

    def __init__(self, parent, config: _config.Config.editor2d, size=wx.DefaultSize, pos=wx.DefaultPosition):
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

        self._grid = _grid.Grid(self)

    def Zoom(self, dx: float, _):
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    def Pan(self, dx: float, dy: float) -> None:
        if self.config.pan.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.pan.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.pan.sensitivity

        dx *= sens
        dy *= sens
        self.camera.Pan(dx, dy)

    def snap_to_grid(self, world_pos: _point.Point) -> _point.Point:
        """
        Snap world coordinates to grid
        """
        if not self.config.grid.snap:
            return world_pos

        spacing = self.config.grid.spacing
        snapped_x = round(world_pos.x / spacing) * spacing
        snapped_y = round(world_pos.y / spacing) * spacing

        return _point.Point(snapped_x, snapped_y)

    def apply_angle_lock(self, start_pos: _point.Point, end_pos: _point.Point) -> _point.Point:
        """
        Apply angle lock to constrain movement to specific angles
        """
        if not self.config.angle.lock:
            return end_pos

        # Calculate delta
        delta = end_pos - start_pos

        # Calculate angle in degrees
        angle_rad = math.atan2(delta.y, delta.x)
        angle_deg = math.degrees(angle_rad)

        # Normalize to 0-360
        if angle_deg < 0:
            angle_deg += 360

        # Round to nearest increment
        locked_angle_deg = round(angle_deg / self.config.angle.lock_increment) * self.config.angle.lock_increment
        locked_angle_rad = math.radians(locked_angle_deg)

        # Calculate distance
        distance = math.sqrt(delta.x * delta.x + delta.y * delta.y)

        # Apply locked angle
        locked_x = start_pos.x + distance * math.cos(locked_angle_rad)
        locked_y = start_pos.y + distance * math.sin(locked_angle_rad)

        return _point.Point(locked_x, locked_y)

    def set_grid_snap(self, value):
        """Set grid snap setting in config"""
        self.config.grid.snap = bool(value)

    def set_angle_lock(self, value):
        """Set angle lock setting in config"""
        self.config.angle.lock = bool(value)

    def set_grid_display(self, value):
        """Set grid display setting in config"""
        self.config.grid.enabled = bool(value)
        self._grid.set(self.config.grid.enabled)
        self.Refresh()

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
            with self.context:
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

        # Calculate visible world bounds based on camera distance
        # The distance controls how much of the world we see
        # Larger distance = see more (zoomed out), smaller distance = see less (zoomed in)
        world_per_pixel = self.camera.distance / 1000.0

        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

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
            GL.glClearColor(0.9600, 0.9568, 0.9372, 1.0)  # Light beige background
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
            self._grid.set(self.config.grid.enabled)

        self._init = True

    def _on_paint(self, _):
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

            self._grid.render(self.camera.distance)

            # Render all objects
            for obj in self._objects:
                obj.obj2d.render_gl()

            # Swap buffers
            self.SwapBuffers()

    def _render_grid(self):
        """Render background grid with major and minor lines that adapt to zoom level"""
        if not self.config.grid.enabled or self.size is None:
            return

        # Calculate grid spacing based on distance (zoom)
        # Grid should be between 20-100 pixels apart for minor lines
        base_spacing = self.config.grid.spacing  # mm - base minor grid spacing
        minor_spacing = base_spacing

        # Calculate how many pixels per world unit
        pixels_per_world = 1000.0 / self.camera.distance
        print(pixels_per_world)
        pixel_spacing = minor_spacing * pixels_per_world

        print(pixel_spacing)
        # Adjust spacing to keep grid visible but not too dense
        while pixel_spacing < 70:
            minor_spacing *= 10
            pixel_spacing = minor_spacing * pixels_per_world
        while pixel_spacing > 400:
            minor_spacing /= 10
            pixel_spacing = minor_spacing * pixels_per_world

        print(minor_spacing)
        print(pixel_spacing)
        # Major grid is 10x minor grid
        major_spacing = minor_spacing * 10

        print(major_spacing)

        # Calculate visible bounds using camera
        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height

        # Round to grid
        minor_start_x = 0
        minor_start_y = 0
        major_start_x = 0
        major_start_y = 0

        # Draw minor grid lines (dashed, thinner, lighter)
        GL.glEnable(GL.GL_LINE_STIPPLE)
        GL.glLineStipple(1, 0x8000)  # Sparser dotted pattern
        GL.glColor4f(0.7098, 0.7098, 0.7098, 1.0)  # Light gray
        GL.glLineWidth(1.5)

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
        GL.glColor4f(0.25, 0.25, 0.25, 1.0)  # Dark gray for contrast
        GL.glLineWidth(1.0)

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
