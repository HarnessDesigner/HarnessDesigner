# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
2D Schematic Editor Canvas using OpenGL

wx.glcanvas.GLCanvas → QOpenGLWidget

Conversion notes (same pattern as canvas3d):
  - initializeGL()  replaces _init_gl() called from EVT_PAINT handler
  - resizeGL(w, h)  replaces EVT_SIZE handler
  - paintGL()       replaces EVT_PAINT / _on_paint
  - SwapBuffers()   implicit — Qt does it automatically
  - makeCurrent()   called by GLContext.acquire() (no explicit SetCurrent)
  - wx.CallAfter    → QTimer.singleShot(0, fn)  (not used here but pattern noted)
  - GetClientSize() → self.width(), self.height()
"""

import math

from PySide6.QtCore import QSize, QTimer, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL

from .. import context as _context
from ... import config as _config
from ...geometry import point as _point
from . import grid as _grid

from .. import events as _events


MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS


class Canvas(QOpenGLWidget):
    """
    2D OpenGL Canvas for Schematic Editor.

    Provides orthographic 2D view with:
    - 1:1 mm mapping (same as 3D canvas)
    - Pan and zoom capabilities
    - Object selection and dragging
    - Point-based coordinate system
    - Snap-to-grid functionality
    """

    # GL signals — same set as canvas3d (mouse/key handlers emit these)
    gl_object_selected = Signal(object)
    gl_object_unselected = Signal(object)
    gl_object_activated = Signal(object)
    gl_object_right_click = Signal(object)
    gl_object_right_dclick = Signal(object)
    gl_object_middle_click = Signal(object)
    gl_object_middle_dclick = Signal(object)
    gl_object_aux1_click = Signal(object)
    gl_object_aux1_dclick = Signal(object)
    gl_object_aux2_click = Signal(object)
    gl_object_aux2_dclick = Signal(object)
    gl_object_drag = Signal(object)
    gl_key_down = Signal(object)
    gl_key_up = Signal(object)
    gl_mouse_move = Signal(object)
    gl_left_down = Signal(object)
    gl_left_up = Signal(object)
    gl_left_dclick = Signal(object)
    gl_right_down = Signal(object)
    gl_right_up = Signal(object)
    gl_right_dclick = Signal(object)
    gl_middle_down = Signal(object)
    gl_middle_up = Signal(object)
    gl_middle_dclick = Signal(object)
    gl_aux1_down = Signal(object)
    gl_aux1_up = Signal(object)
    gl_aux1_dclick = Signal(object)
    gl_aux2_down = Signal(object)
    gl_aux2_up = Signal(object)
    gl_aux2_dclick = Signal(object)
    gl_capture_lost = Signal(object)

    def __init__(self, parent, config: "_config.Config.editor2d", size: QSize = None):
        super().__init__(parent)

        # Walk up to mainframe
        w = parent

        while w is not None and not hasattr(w, 'editor2d'):
            w = w.parent()

        self.mainframe = w if w is not None else parent

        self.config = config
        self._init = False
        self.context = _context.GLContext(self)

        from . import camera as _camera
        self.camera = _camera.Camera2D(self)

        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._is_panning = False
        self._is_dragging = False

        self._objects = []
        self._selected = None
        self._hovered = None
        self._ref_count = 0

        self.size = None

        from . import mouse_handler as _mouse_handler
        self._mouse_handler = _mouse_handler.MouseHandler2D(self)

        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

        self._grid = _grid.Grid(self)

        if size is not None:
            self.resize(size)

    # ------------------------------------------------------------------
    # Camera movement
    # ------------------------------------------------------------------

    def Zoom(self, dx: float, _=None):
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    def Pan(self, dx: float, dy: float) -> None:
        if self.config.pan.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.pan.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.pan.sensitivity
        self.camera.Pan(dx * sens, dy * sens)

    # ------------------------------------------------------------------
    # Grid / snap helpers (unchanged)
    # ------------------------------------------------------------------

    def snap_to_grid(self, world_pos: _point.Point) -> _point.Point:
        if not self.config.grid.snap:
            return world_pos

        spacing = self._grid.grid_spacing

        return _point.Point(
            round(world_pos.x / spacing) * spacing,
            round(world_pos.y / spacing) * spacing,
        )

    def apply_angle_lock(self, start_pos: _point.Point, end_pos: _point.Point) -> _point.Point:
        if not self.config.angle.lock:
            return end_pos

        delta = end_pos - start_pos
        angle_rad = math.atan2(delta.y, delta.x)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360

        locked = round(angle_deg / self.config.angle.lock_increment) * self.config.angle.lock_increment
        locked_rad = math.radians(locked)
        dist = math.sqrt(delta.x ** 2 + delta.y ** 2)

        return _point.Point(
            start_pos.x + dist * math.cos(locked_rad),
            start_pos.y + dist * math.sin(locked_rad),
        )

    def set_grid_snap(self, value):
        self.config.grid.snap = bool(value)

    def set_angle_lock(self, value):
        self.config.angle.lock = bool(value)

    def set_grid_display(self, value):
        self.config.grid.enabled = bool(value)
        self._grid.set(self.config.grid.enabled)
        self.update()

    # ------------------------------------------------------------------
    # Object management
    # ------------------------------------------------------------------

    def set_selected(self, obj):
        self._selected = obj

    def get_selected(self):
        return self._selected

    def add_object(self, obj):
        if obj not in self._objects:
            self._objects.append(obj)
            self.update()

    def remove_object(self, obj):
        try:
            self._objects.remove(obj)
            if self._selected == obj:
                self._selected = None
            if self._hovered == obj:
                self._hovered = None
            self.update()
        except ValueError:
            pass

    @property
    def objects(self):
        return self._objects

    # ------------------------------------------------------------------
    # Reference-counting context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        if self._ref_count:
            return

        self.update()

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # ------------------------------------------------------------------

    def initializeGL(self):
        """One-time GL setup (replaces _init_gl called from _on_paint).
        Qt guarantees the context is already current here.
        """
        GL.glClearColor(0.9600, 0.9568, 0.9372, 1.0)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
        GL.glDisable(GL.GL_DEPTH_TEST)

        if self.size:
            GL.glViewport(0, 0, self.size[0], self.size[1])

        self._setup_projection()
        self._grid.set(self.config.grid.enabled)

    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize (replaces EVT_SIZE handler).
        Context is already current here.
        """
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)
        self._setup_projection()

    def paintGL(self):
        """Render one frame (replaces EVT_PAINT / _on_paint).
        Context is already current here.
        """
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self._setup_projection()
        self._grid.render(self.camera.distance)

        for obj in self._objects:
            obj.obj2d.render_gl()
        # Qt handles SwapBuffers automatically.

    def cleanup(self):
        """Clean up GL resources before widget destruction."""
        # Import here to avoid circular dependency
        from ..vbo import VBOHandler
        
        # Make sure we have a current context before cleaning up
        self.makeCurrent()
        
        # Clean up all VBOHandler instances for this context
        VBOHandler.cleanup_all_for_context()
        
        # Release context
        self.doneCurrent()

    def closeEvent(self, event):
        """Handle widget close event - clean up OpenGL resources."""
        self.cleanup()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Projection (unchanged)
    # ------------------------------------------------------------------

    def _setup_projection(self):
        if self.size is None:
            return
        width, height = self.size
        if width == 0 or height == 0:
            return

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height

        GL.glOrtho(left, right, bottom, top, -1.0, 1.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
