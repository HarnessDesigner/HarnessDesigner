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

import numpy as np
from PySide6.QtCore import QSize, QTimer, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL

from .. import context as _context
from .. import shaders as _shaders
from ... import config as _config
from ...geometry import point as _point
from . import grid as _grid

from .. import events as _events
from ... import check_types as _check_types


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

    @_check_types.do
    def __init__(self, parent, config: _config.Config.editor2d, size: QSize = None):
        """Initialise the :class:`Canvas` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor2d`
        :param size: Value for ``size``.
        :type size: :class:`QSize`
        """
        super().__init__(parent)

        # Walk up to mainframe
        w = parent

        while w is not None and not hasattr(w, 'editor2d'):
            w = w.parent()

        self.mainframe = w if w is not None else parent

        self.config = config
        self._init = False
        self.context = _context.GLContext(self)
        self._program = None

        from . import camera as _camera
        self.camera = _camera.Camera(self)

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

    @_check_types.do
    def Zoom(self, dx: float, _=None):
        """Execute the zoom operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: float
        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    @_check_types.do
    def Pan(self, dx: float, dy: float) -> None:
        """Execute the pan operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: float
        :param dy: Value for ``dy``.
        :type dy: float
        """
        if self.config.pan.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.pan.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.pan.sensitivity
        self.camera.Pan(dx * sens, dy * sens)

    # ------------------------------------------------------------------
    # Grid / snap helpers (unchanged)
    # ------------------------------------------------------------------

    @_check_types.do
    def snap_to_grid(self, world_pos: _point.Point) -> _point.Point:
        """Execute the snap to grid operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param world_pos: Value for ``world_pos``.
        :type world_pos: :class:`_point.Point`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if not self.config.grid.snap:
            return world_pos

        spacing = self._grid.grid_spacing

        return _point.Point(
            round(world_pos.x / spacing) * spacing,
            round(world_pos.y / spacing) * spacing,
        )

    @_check_types.do
    def apply_angle_lock(self, start_pos: _point.Point, end_pos: _point.Point) -> _point.Point:
        """Execute the apply angle lock operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param start_pos: Value for ``start_pos``.
        :type start_pos: :class:`_point.Point`
        :param end_pos: Value for ``end_pos``.
        :type end_pos: :class:`_point.Point`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
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

    @_check_types.do
    def set_grid_snap(self, value):
        """Set the grid snap.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self.config.grid.snap = bool(value)

    @_check_types.do
    def set_angle_lock(self, value):
        """Set the angle lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self.config.angle.lock = bool(value)

    @_check_types.do
    def set_grid_display(self, value):
        """Set the grid display.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self.config.grid.enabled = bool(value)
        self._grid.set(self.config.grid.enabled)
        self.update()

    # ------------------------------------------------------------------
    # Object management
    # ------------------------------------------------------------------

    @_check_types.do
    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._selected = obj

    @_check_types.do
    def get_selected(self):
        """Return the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._selected

    @_check_types.do
    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        if obj not in self._objects:
            self._objects.append(obj)
            self.update()

    @_check_types.do
    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        try:
            self._objects.remove(obj)
            if self._selected == obj:
                self._selected = None
            if self._hovered == obj:
                self._hovered = None
            self.update()
        except ValueError:
            pass

    @_check_types.do
    def clear(self) -> None:
        """Drop every scene object in bulk, without touching the database.

        Used when tearing down the current project so a different one can
        load in its place (see ``ui.mainframe.MainFrame.unload``).
        """
        self._objects = []
        self._selected = None
        self._hovered = None
        self.update()

    @property
    @_check_types.do
    def objects(self):
        """Return the objects.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._objects

    # ------------------------------------------------------------------
    # Reference-counting context manager
    # ------------------------------------------------------------------

    @_check_types.do
    def __enter__(self):
        """Enter the managed context.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._ref_count += 1
        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the managed context.

        UNKNOWN details are inferred from the callable name and signature.

        :param exc_type: Value for ``exc_type``.
        :type exc_type: UNKNOWN
        :param exc_val: Value for ``exc_val``.
        :type exc_val: UNKNOWN
        :param exc_tb: Value for ``exc_tb``.
        :type exc_tb: UNKNOWN
        """
        self._ref_count -= 1

    @_check_types.do
    def Refresh(self, *args, **kwargs):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        if self._ref_count:
            return

        self.update()

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # ------------------------------------------------------------------

    @_check_types.do
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
        self._program = _shaders.compile_schematic2d_program()

    @_check_types.do
    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize (replaces EVT_SIZE handler).
        Context is already current here.
        """
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)
        self._setup_projection()

    @_check_types.do
    def paintGL(self):
        """Render one frame (replaces EVT_PAINT / _on_paint).
        Context is already current here.

        Two rendering paths coexist while object types migrate from the
        legacy immediate-mode path one piece at a time (see
        objects.objects2d.base2d.Base2D): objects with a VBO
        (obj.obj2d.vbo is not None) render via _render_vbo_objects()'s
        schematic2d-shader pass; everything else still renders through its
        own render_gl() below, unchanged.
        """
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self._setup_projection()
        self.camera._update_views()  # NOQA -- picks up glOrtho bounds set above
        self._grid.render(self.camera.distance)

        for obj in self._objects:
            if obj.obj2d.vbo is not None:
                continue
            obj.obj2d.render_gl()

        self._render_vbo_objects()
        # Qt handles SwapBuffers automatically.

    @_check_types.do
    def _projection_matrix(self) -> np.ndarray:
        """Build the orthographic projection matrix for the schematic2d
        shader, matching :meth:`_setup_projection`'s ``glOrtho`` bounds
        exactly (same ``camera.distance``/``camera.x``/``camera.y``/
        ``size`` inputs, same ``near=-1, far=1``) -- mirrors
        ``gl.canvas_pegboard.canvas.Canvas._pegboard_projection_matrix``.
        """
        width, height = self.size
        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height
        near, far = -1.0, 1.0

        return np.array([
            [2.0 / (right - left), 0.0, 0.0, -(right + left) / (right - left)],
            [0.0, 2.0 / (top - bottom), 0.0, -(top + bottom) / (top - bottom)],
            [0.0, 0.0, -2.0 / (far - near), -(far + near) / (far - near)],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

    @_check_types.do
    def _render_vbo_objects(self):
        """Render every VBO-backed object (``obj.obj2d.vbo is not None``)
        under the schematic2d shader -- mirrors
        ``gl.canvas_pegboard.canvas.Canvas._render_objects``' uniform-
        setting contract exactly (``objectPosition``/``objectRotation``/
        ``objectScale`` per object, same per-frame lighting/camera
        uniforms).

        A ``Wire`` without a completed connection (Terminal or Splice) at
        both ends is skipped -- see ``objects/wire.py``'s
        ``Wire.is_connected`` -- so an in-progress/dangling wire simply
        doesn't appear in the schematic. Every other object type has no
        ``is_connected`` attribute at all, so ``getattr(..., True)``
        leaves them unaffected.
        """
        if self._program is None:
            return

        vbo_objects = [
            obj for obj in self._objects
            if obj.obj2d.vbo is not None and getattr(obj, 'is_connected', True)
        ]
        if not vbo_objects:
            return

        if self.size is None:
            return

        width, height = self.size
        if width == 0 or height == 0:
            return

        GL.glUseProgram(self._program)

        projection = self._projection_matrix()
        view = np.eye(4, dtype=np.float32)

        proj_loc = GL.glGetUniformLocation(self._program, "projection")
        view_loc = GL.glGetUniformLocation(self._program, "view")
        flip_y_loc = GL.glGetUniformLocation(self._program, "flipY")
        camera_loc = GL.glGetUniformLocation(self._program, "cameraPos2D")
        light_color_loc = GL.glGetUniformLocation(self._program, "lightColor")
        light_intensity_loc = GL.glGetUniformLocation(self._program, "lightIntensity")
        render_mode_loc = GL.glGetUniformLocation(self._program, "renderMode")

        GL.glUniformMatrix4fv(proj_loc, 1, GL.GL_FALSE, np.ascontiguousarray(projection.T))
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, np.ascontiguousarray(view.T))

        # World coords (Y-up), not screen coords -- same convention
        # gl.canvas_pegboard.canvas uses.
        GL.glUniform1i(flip_y_loc, 0)
        GL.glUniform2f(camera_loc, self.camera.x, self.camera.y)
        GL.glUniform3f(light_color_loc, 1.0, 1.0, 1.0)
        GL.glUniform1f(light_intensity_loc, 1.0)
        GL.glUniform1i(render_mode_loc, 0)  # filled

        pos_loc = GL.glGetUniformLocation(self._program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(self._program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(self._program, "objectScale")
        normal_loc = GL.glGetUniformLocation(self._program, "normalMode")

        for obj in vbo_objects:
            obj2d = obj.obj2d
            obj2d.material.set(self._program)
            obj2d._render_geometry(self._program, pos_loc, rot_loc, scale_loc, normal_loc)  # NOQA

            # Object-owned extras (e.g. Housing2D's pin markers/terminal-
            # name rows/corner label) drawn under this same bound program/
            # uniform contract, right after the object's own primitive.
            render_extras = getattr(obj2d, 'render_extras', None)
            if render_extras is not None:
                render_extras(self._program, pos_loc, rot_loc, scale_loc, normal_loc)

        GL.glUseProgram(0)

    # ------------------------------------------------------------------
    # Projection (unchanged)
    # ------------------------------------------------------------------

    @_check_types.do
    def _setup_projection(self):
        """Execute the setup projection operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
