# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg Board Editor Canvas using OpenGL

Phase 1 skeleton: camera/pan/zoom/grid plumbing only, mirroring
gl.canvas2d.canvas.Canvas exactly where its pattern is canvas-agnostic
(GLContext usage, Camera2D-based orthographic projection, background
clear, ref-counted Refresh()). No peg-board scene-object rendering,
VBO/model reuse, or DB queries happen here -- that is a later task's job,
built on top of the extension points marked below.

wx.glcanvas.GLCanvas -> QOpenGLWidget

  - initializeGL()  one-time GL setup, called once the context is current
  - resizeGL(w, h)  replaces EVT_SIZE handler
  - paintGL()       replaces EVT_PAINT / _on_paint
  - SwapBuffers()   implicit -- Qt does it automatically
  - makeCurrent()   called by GLContext.acquire() (no explicit SetCurrent)
  - GetClientSize() -> self.width(), self.height()
"""

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QSize, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL

from .. import context as _context
from .. import shaders as _shaders
from ... import config as _config
from ...geometry import point as _point
from ..canvas2d import grid as _grid


if TYPE_CHECKING:
    from . import layout_graph as _layout_graph


MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS


class Canvas(QOpenGLWidget):
    """
    Peg Board OpenGL Canvas.

    Provides the same orthographic top-down view as the 2D schematic
    canvas:
    - 1:1 mm mapping (same distance/1000.0 world-per-pixel convention as
      Camera2D)
    - Pan and zoom, via mouse (MouseHandlerPegBoard) and keyboard
      (KeyHandler)
    - Background reference grid (reuses gl.canvas2d.grid.Grid unchanged --
      it is canvas-agnostic: it only ever touches ``canvas.config``,
      ``canvas.context`` and ``canvas.Refresh()``)

    No scene-object selection/dragging/rendering exists yet -- see the
    "TODO" markers in this file and in mouse_handler.py for where a later
    task hooks that in.
    """

    # GL signals -- same set as canvas2d/canvas3d (mouse/key handlers emit
    # these). Declared now, even though nothing emits the gl_object_* ones
    # yet, so a later task wiring the dock doesn't also need to add them.
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

    def __init__(self, parent, config: "_config.Config.editor_pegboard" = None,
                 size: QSize = None):
        """Initialise the :class:`Canvas` instance.

        :param parent: Parent widget.
        :type parent: UNKNOWN
        :param config: Peg board editor config section. Defaults to
            ``Config.editor_pegboard`` so the canvas is directly usable
            standalone (no host dock exists yet).
        :type config: :class:`_config.Config.editor_pegboard`
        :param size: Optional initial size.
        :type size: :class:`QSize`
        """
        super().__init__(parent)

        # Walk up to mainframe -- same convention as canvas2d.canvas.Canvas.
        # `mainframe.editor_pegboard` doesn't exist yet (the dock is a
        # separate, later task); until it does this gracefully falls back
        # to `parent`, exactly like canvas2d does today.
        w = parent

        while w is not None and not hasattr(w, 'editor_pegboard'):
            w = w.parent()

        self.mainframe = w if w is not None else parent

        self.config = config if config is not None else _config.Config.editor_pegboard
        self._init = False
        self.context = _context.GLContext(self)

        from . import camera as _camera
        self.camera = _camera.Camera2D(self)

        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._is_panning = False

        self._ref_count = 0
        self.size = None

        from . import mouse_handler as _mouse_handler
        self._mouse_handler = _mouse_handler.MouseHandlerPegBoard(self)

        from . import key_handler as _key_handler
        self._key_handler = _key_handler.KeyHandler(self)

        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

        self._grid = _grid.Grid(self)

        # Phase 1 static peg-board scene state -- see load_project() and
        # _render_objects() below. self._pegboard_program is compiled once
        # the GL context exists (initializeGL); self._anchors starts empty
        # until a later task's editor dock calls load_project(project).
        self._pegboard_program = None
        self._anchors: list["_layout_graph.PegboardAnchor"] = []

        if size is not None:
            self.resize(size)

    # ------------------------------------------------------------------
    # Camera movement
    # ------------------------------------------------------------------

    def Zoom(self, dx: float, _=None):
        """Execute the zoom operation.

        :param dx: Zoom delta.
        :type dx: float
        :param _: Unused (kept for signature parity with Camera2D consumers).
        :type _: UNKNOWN
        """
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    def Pan(self, dx: float, dy: float) -> None:
        """Execute the pan operation.

        :param dx: Horizontal screen-pixel delta.
        :type dx: float
        :param dy: Vertical screen-pixel delta.
        :type dy: float
        """
        if self.config.pan.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.pan.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.pan.sensitivity
        self.camera.Pan(dx * sens, dy * sens)

    # ------------------------------------------------------------------
    # Grid / snap helpers
    # ------------------------------------------------------------------

    def snap_to_grid(self, world_pos: _point.Point) -> _point.Point:
        """Snap a world position to the current grid spacing.

        :param world_pos: Position to snap.
        :type world_pos: :class:`_point.Point`
        :returns: Snapped position (unchanged if grid snap is disabled).
        :rtype: :class:`_point.Point`
        """
        if not self.config.grid.snap:
            return world_pos

        manual_spacing = self.config.grid.manual_snap_spacing
        spacing = self._grid.grid_spacing if manual_spacing is None else manual_spacing

        return _point.Point(
            round(world_pos.x / spacing) * spacing,
            round(world_pos.y / spacing) * spacing,
        )

    def set_grid_snap(self, value) -> None:
        """Enable/disable snap-to-grid.

        :param value: New snap-to-grid state.
        :type value: UNKNOWN
        """
        self.config.grid.snap = bool(value)

    def set_grid_display(self, value) -> None:
        """Show/hide the reference grid.

        :param value: New grid-visibility state.
        :type value: UNKNOWN
        """
        self.config.grid.enabled = bool(value)
        self._grid.set(self.config.grid.enabled)
        self.update()

    # ------------------------------------------------------------------
    # Reference-counting context manager (Camera2D calls Refresh() on
    # focal-position change; ref-counting lets a caller batch several
    # camera moves and only repaint once)
    # ------------------------------------------------------------------

    def __enter__(self):
        """Enter the managed context."""
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the managed context.

        :param exc_type: Exception type, if any.
        :type exc_type: UNKNOWN
        :param exc_val: Exception value, if any.
        :type exc_val: UNKNOWN
        :param exc_tb: Exception traceback, if any.
        :type exc_tb: UNKNOWN
        """
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        """Repaint the canvas, unless a batching context is still open.

        :param args: Unused, kept for call-site parity with wx-style Refresh.
        :type args: UNKNOWN
        :param kwargs: Unused, kept for call-site parity with wx-style Refresh.
        :type kwargs: UNKNOWN
        """
        if self._ref_count:
            return

        self.update()

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # ------------------------------------------------------------------

    def initializeGL(self):
        """One-time GL setup. Qt guarantees the context is already current here."""
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

        self._pegboard_program = _shaders.compile_schematic2d_program()

    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize. Context is already current here."""
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)
        self._setup_projection()

    def paintGL(self):
        """Render one frame. Context is already current here."""
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self._setup_projection()
        self._grid.render(self.camera.distance)
        self._render_objects()
        # Qt handles SwapBuffers automatically.

    def load_project(self, project) -> None:
        """Build this canvas's Phase 1 static top-down anchor list from
        *project* and repaint.

        Called once a project is open and its 3D scene objects exist (a
        later task wires this up from the peg board editor dock, once it
        exists). Safe to call again later (e.g. after parts are added or
        removed) -- it always rebuilds the full anchor list from scratch.

        :param project: The currently open project (``mainframe.project``).
        :type project: :class:`harness_designer.objects.project.Project`
        """
        from . import layout_graph as _layout_graph

        self._anchors = _layout_graph.build_anchors(project)
        self.update()

    def center_on_object(self, obj) -> None:
        """Pan the camera so *obj*'s anchor is centered, keeping the
        current zoom/distance -- used by ``mainframe._set_selected()`` to
        bring a selection into view without disturbing the user's zoom.

        No-op if *obj* has no anchor on this canvas (not a peg-board-
        renderable part, or the anchor list hasn't been built yet).

        :param obj: The wrapper whose anchor should be centered.
        :type obj: :class:`harness_designer.objects.object_base.ObjectBase`
        """
        for anchor in self._anchors:
            if anchor.obj is obj:
                self.camera.x = anchor.x
                self.camera.y = anchor.z
                return

    @property
    def anchors(self) -> list["_layout_graph.PegboardAnchor"]:
        """Return the current Phase 1 static anchor list.

        Public read accessor for :attr:`_anchors` -- mirrors
        ``gl.canvas2d.canvas.Canvas.objects`` -- so
        ``MouseHandlerPegBoard`` can hit-test/select without reaching into
        a private attribute across module boundaries.

        :returns: Property value.
        :rtype: list[:class:`_layout_graph.PegboardAnchor`]
        """
        return self._anchors

    def _pegboard_projection_matrix(self) -> np.ndarray:
        """Build the orthographic projection matrix for the schematic2d
        shader, matching :meth:`_setup_projection`'s legacy
        ``glOrtho``/``glMatrixMode`` bounds exactly (same
        ``camera.distance``/``camera.x``/``camera.y``/``size`` inputs,
        same ``near=-1, far=1``).

        :returns: Row-major 4x4 orthographic projection matrix.
        :rtype: numpy.ndarray
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

    def _render_objects(self):
        """Render placed peg-board scene objects.

        Phase 1: a read-only static top-down render of every anchor in
        ``self._anchors`` (see :meth:`load_project` and
        ``gl.canvas_pegboard.layout_graph.build_anchors``), reusing the
        exact same VBOs/materials the 3D editor renders with under the
        schematic2d shader -- mirroring the uniform-setting contract of
        ``objects.objects3d.base3d.Base3D._render_geometry``/``render``.

        No object picking/dragging exists yet (Phase 1 is READ-ONLY) --
        that is a later task's job, once the peg-board scene-object model
        supports it.
        """
        if self._pegboard_program is None or not self._anchors:
            return

        if self.size is None:
            return

        width, height = self.size
        if width == 0 or height == 0:
            return

        GL.glUseProgram(self._pegboard_program)

        projection = self._pegboard_projection_matrix()
        view = np.eye(4, dtype=np.float32)

        proj_loc = GL.glGetUniformLocation(self._pegboard_program, "projection")
        view_loc = GL.glGetUniformLocation(self._pegboard_program, "view")
        flip_y_loc = GL.glGetUniformLocation(self._pegboard_program, "flipY")
        camera_loc = GL.glGetUniformLocation(self._pegboard_program, "cameraPos2D")
        light_color_loc = GL.glGetUniformLocation(self._pegboard_program, "lightColor")
        light_intensity_loc = GL.glGetUniformLocation(self._pegboard_program, "lightIntensity")
        render_mode_loc = GL.glGetUniformLocation(self._pegboard_program, "renderMode")

        # gl.canvas3d.canvas.Canvas always builds its matrices already
        # column-major and uploads with GL_FALSE -- match that convention
        # here too (transpose the row-major array built above ourselves,
        # rather than relying on the transpose flag) instead of mixing
        # conventions across the codebase.
        GL.glUniformMatrix4fv(proj_loc, 1, GL.GL_FALSE, np.ascontiguousarray(projection.T))
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, np.ascontiguousarray(view.T))

        # World coords (Y-up), not screen coords -- matches this canvas's
        # world-unit-direct _setup_projection convention (no flip).
        GL.glUniform1i(flip_y_loc, 0)
        GL.glUniform2f(camera_loc, self.camera.x, self.camera.y)
        GL.glUniform3f(light_color_loc, 1.0, 1.0, 1.0)
        GL.glUniform1f(light_intensity_loc, 1.0)
        GL.glUniform1i(render_mode_loc, 0)  # filled

        # Per-object uniform locations don't change between anchors within
        # this one program -- fetched once per frame rather than once per
        # anchor.
        pos_loc = GL.glGetUniformLocation(self._pegboard_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(self._pegboard_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(self._pegboard_program, "objectScale")
        normal_loc = GL.glGetUniformLocation(self._pegboard_program, "normalMode")

        for anchor in self._anchors:
            # Selection highlight: reuse the exact same
            # Base3D._selected_material (Config.editor3d.selected_color)
            # the 3D editor already swaps to on selection -- read live via
            # anchor.obj.obj3d.material instead of the anchor's own
            # snapshotted ``material`` field, since that snapshot is only
            # rebuilt on load_project() and would otherwise go stale the
            # moment selection changes from another editor. Only the
            # selected anchor pays this extra hop; every other anchor
            # keeps using its snapshotted material as before.
            if anchor.obj.is_selected:
                material = anchor.obj.obj3d.material
            else:
                material = anchor.material

            material.set(self._pegboard_program)

            GL.glUniform3f(pos_loc, anchor.x, 0.0, anchor.z)
            GL.glUniform4f(rot_loc, anchor.rotation.w, anchor.rotation.x,
                           anchor.rotation.y, anchor.rotation.z)
            GL.glUniform3f(scale_loc, *anchor.scale.as_float)
            GL.glUniform1i(normal_loc, int(anchor.smooth))

            # Both PooledVBOHandler and NonPooledVBOHandler auto-acquire
            # their VAO for the current GL context inside render() itself
            # -- no explicit acquire() call needed here.
            anchor.vbo.render()

        GL.glUseProgram(0)

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def _setup_projection(self):
        """Set up the top-down orthographic projection from the camera."""
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
