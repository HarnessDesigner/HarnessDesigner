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
from . import mouse_handler as _mouse_handler


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

    # this variable is actually an instance variable and is only here
    # to make an IDE happy so so autocomplete will work properly
    config = None

    # String (forward-ref) annotation -- not just style: the attribute name
    # and the imported module's alias are both "_mouse_handler", so a live
    # (non-string) annotation here resolves the module reference against
    # this not-yet-assigned class attribute instead of the actual module,
    # raising AttributeError: 'NoneType' object has no attribute
    # 'MouseHandler' at class-definition time.
    _mouse_handler: "_mouse_handler.MouseHandler" = None

    # TODO: move mainframe parameter to after the parent.
    @_check_types.do
    def __init__(self, parent, mainframe, config, size: QSize = None):
        """
        Initialise the :class:`Canvas` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor2d`
        :param size: Value for ``size``.
        :type size: :class:`QSize`
        :param mainframe: The real ``MainFrame``, passed straight down
            from ``gl.canvas2d.canvas2d.Canvas2D.__init__`` (which
            already receives it as its own ``parent`` argument) --
            no need to rediscover it by walking the Qt parent chain
            here. Falls back to *parent* only when omitted entirely
            (e.g. standalone/test construction with no real MainFrame
            in the picture at all).
        :type mainframe: UNKNOWN
        """
        super().__init__(parent)

        self.mainframe = mainframe

        self.config = config
        self._init = False
        self.context = _context.GLContext(self)

        # this gets set in the initializeGL function. That function needs to be
        # overridden by the subclass to initilize the shader program
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

        # Rotation gizmo lifecycle -- shared by every 2D-plane editor (see
        # gl.canvas2d.rotation_ring.RotationRing's module docstring for why
        # one gizmo class covers schematic and peg board both).
        # self._rotation_gizmo_target is the object/anchor currently
        # showing its rotate ring, or None. self._rotation_gizmo is the
        # actual GPU-side gizmo -- built lazily (needs a current GL
        # context) from paintGL() rather than at enter_rotation_mode() call
        # time, mirroring self._grid's own deferred-build pattern;
        # self._rotation_gizmo_dirty flags that a (re)build is pending.
        # self._rotation_gizmo_degrees is the live, in-progress rotation
        # (degrees) the mouse handler drives during a handle drag.
        self._rotation_gizmo_target = None
        self._rotation_gizmo = None
        self._rotation_gizmo_dirty = False
        self._rotation_gizmo_degrees = 0.0

        self._size = size

        from . import key_handler as _key_handler
        self._key_handler = _key_handler.KeyHandler(self)

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
        """
        Execute the zoom operation.

        :param dx: Value for ``dx``.
        :type dx: float

        :param _: Value for ``_``.
        """

        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    @_check_types.do
    def Pan(self, dx: float, dy: float) -> None:
        """
        Execute the pan operation.

        :param dx: mouse delta x.
        :type dx: float

        :param dy: mouse delta y.
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
        """Snap a world position to the current grid spacing.

        :param world_pos: Position to snap.
        :type world_pos: :class:`_point.Point`

        :returns: Snapped position (unchanged if grid snap is disabled).
        :rtype: :class:`_point.Point`
        """

        # TODO: Check to see if this needs to be updated to use x and z as
        #       the snapping axes.

        if not self.config.grid.snap:
            return world_pos

        manual_spacing = self.config.grid.manual_snap_spacing
        spacing = self._grid.grid_spacing if manual_spacing is None else manual_spacing

        return _point.Point(
            round(world_pos.x / spacing) * spacing,
            round(world_pos.y / spacing) * spacing)

    @_check_types.do
    def set_grid_snap(self, value: bool | int) -> None:
        """
        Set the grid snap.

        :param value: True to enable grid snapping, False otherwise.
        :type value: bool | int
        """
        self.config.grid.snap = bool(value)

    @_check_types.do
    def set_angle_lock(self, value: bool | int) -> None:
        """
        Set the angle lock.

        :param value: True to enable angle locking, False otherwise.
        :type value: bool | int
        """

        self.config.angle.lock = bool(value)

    @_check_types.do
    def set_grid_display(self, value: bool | int) -> None:
        """
        Set the grid display.

        :param value: True to enable the grid, False otherwise.
        :type value: bool | int
        """

        self.config.grid.enabled = bool(value)
        self._grid.set(self.config.grid.enabled)
        self.update()

    # ------------------------------------------------------------------
    # Object management
    # ------------------------------------------------------------------

    @_check_types.do
    def set_selected(self, obj) -> None:
        """
        Set the selected object

        :param obj: Object instance toset as selected.
        """

        self._selected = obj

    @_check_types.do
    def get_selected(self):
        """
        Get the currently selected object.

        :returns: Selected object or None
        """

        return self._selected

    @_check_types.do
    def add_object(self, obj) -> None:
        """
        Add an object. to the rendering pipeline.

        :param obj: Object instance.
        """

        if obj not in self._objects:
            self._objects.append(obj)
            self.update()

    @_check_types.do
    def remove_object(self, obj) -> None:
        """
        Remove object from the rendering pipeline.

        :param obj: Object instance.
        """

        try:
            self._objects.remove(obj)
            if self._selected == obj:
                self._selected = None
            if self._hovered == obj:
                self._hovered = None

            if self._rotation_gizmo_target is getattr(obj, 'obj2d', None):
                self.exit_rotation_mode()

            self.update()
        except ValueError:
            # obj wasn't in self._objects (already removed, or never
            # added) -- a silent no-op, matching
            # gl.canvas3d.canvas.Canvas.remove_object's same idempotent
            # try/except ValueError pattern.
            pass

    @_check_types.do
    def clear(self) -> None:
        """
        Drop every scene object in bulk, without touching the database.

        Used when tearing down the current project so a different one can
        load in its place (see ``ui.mainframe.MainFrame.unload``).
        """

        self.exit_rotation_mode()

        self._objects = []
        self._selected = None
        self._hovered = None
        self.update()

    @property
    @_check_types.do
    def objects(self) -> list:
        """
        Get all of the objects in the rendering pipeline.

        :rtype: list
        """
        return self._objects

    # ------------------------------------------------------------------
    # Rotation gizmo lifecycle (shared by every 2D-plane editor -- see
    # gl.canvas2d.rotation_ring.RotationRing)
    # ------------------------------------------------------------------

    @property
    @_check_types.do
    def rotation_gizmo_target(self):
        """Return the object/anchor currently showing its rotate ring, or
        ``None``.

        Public read accessor for :attr:`_rotation_gizmo_target` so the
        mouse handler can tell whether "rotation mode" is active without
        reaching into a private attribute.
        """
        return self._rotation_gizmo_target

    @property
    @_check_types.do
    def rotation_gizmo_degrees(self) -> float:
        """Return the active gizmo's live, in-progress rotation, in degrees.

        Public read accessor for :attr:`_rotation_gizmo_degrees` -- used by
        the mouse handler as the starting value when a handle drag is
        armed (read live off the target's own bound ``angle.y`` at
        drag-arm time) and again to keep the gizmo's own render
        orientation current.
        """
        return self._rotation_gizmo_degrees

    @_check_types.do
    def enter_rotation_mode(self, target) -> None:
        """Show the rotate-ring gizmo for *target*.

        Seeds :attr:`_rotation_gizmo_degrees` from *target*'s live
        ``angle.y``. The actual GPU-side gizmo is built lazily by
        :meth:`_rebuild_rotation_gizmo` (needs a current GL context) --
        this only flags the pending build (:attr:`_rotation_gizmo_dirty`),
        mirroring :attr:`_grid`'s own deferred-build pattern.

        A no-op if *target* is already the active gizmo's target. Any
        previously active gizmo (for a different target) is exited first.

        :param target: The object/anchor to show the rotate ring for.
        """

        if self._rotation_gizmo_target is target:
            return

        self.exit_rotation_mode()

        self._rotation_gizmo_target = target
        self._rotation_gizmo_degrees = float(target.angle.y)
        self._rotation_gizmo_dirty = True
        self.update()

    @_check_types.do
    def exit_rotation_mode(self) -> None:
        """Hide the rotate-ring gizmo, releasing its GL buffers.

        Safe to call whether or not a gizmo is currently active (a no-op
        when it isn't), and safe to call from outside ``paintGL()`` (e.g.
        ``remove_object``/``clear``, the mouse handler) -- the release is
        wrapped in ``with self.context:`` so it acquires the GL context
        itself rather than assuming one is already current.
        """

        if self._rotation_gizmo is not None:
            with self.context:
                self._rotation_gizmo.release()
            self._rotation_gizmo = None

        self._rotation_gizmo_target = None
        self._rotation_gizmo_dirty = False
        self.update()

    @_check_types.do
    def update_rotation_drag(self, rotation_deg: float) -> None:
        """Update the live, in-progress rotation during a drag.

        Updates :attr:`_rotation_gizmo_degrees` (read by
        :meth:`_rebuild_rotation_gizmo`/the gizmo's own ``render`` to
        orient it) and writes straight to the target's live ``angle.y`` --
        a live, DB-backed ``Angle`` that persists immediately via its own
        bound callback (and, for a 90-degree-locked type like Housing,
        self-corrects to the nearest 90 degrees on every single write --
        see ``Angle2DMixin._update_angle2d`` -- so the read-back below
        keeps the gizmo showing the true persisted value even when it
        differs from what was requested). A no-op if no rotation gizmo is
        currently active.

        :param rotation_deg: The new live rotation, in degrees.
        :type rotation_deg: float
        """

        target = self._rotation_gizmo_target
        if target is None:
            return

        target.angle.y = rotation_deg
        self._rotation_gizmo_degrees = float(target.angle.y)

        self.update()

    @_check_types.do
    def rotation_gizmo_handle_world_pos(self) -> _point.Point | None:
        """Return the active gizmo's grab handle world position, or ``None``.

        ``None`` when no rotation gizmo is active, or when one is active
        but not yet built (the frame between :meth:`enter_rotation_mode`
        and the next :meth:`_rebuild_rotation_gizmo` call) -- the mouse
        handler treats either case as "nothing to hit-test".
        """

        if self._rotation_gizmo is None or self._rotation_gizmo_target is None:
            return None

        return self._rotation_gizmo.handle_world_pos(self._rotation_gizmo_degrees)

    @_check_types.do
    def _rebuild_rotation_gizmo(self) -> None:
        """(Re)build the GPU-side rotation-ring gizmo for whichever target
        is currently in "rotation mode" (:attr:`_rotation_gizmo_target`).

        Old GL buffers are always released first. A no-op build (gizmo
        left ``None``) if no target is currently in rotation mode -- can
        happen if :meth:`exit_rotation_mode` raced this call, though in
        practice both only ever run on the GUI thread. Requires a current
        GL context -- only ever called from a subclass's ``_render_scene``.
        """

        from . import rotation_ring as _rotation_ring

        if self._rotation_gizmo is not None:
            self._rotation_gizmo.release()
            self._rotation_gizmo = None

        target = self._rotation_gizmo_target
        if target is not None:
            self._rotation_gizmo = _rotation_ring.RotationRing(target)

        self._rotation_gizmo_dirty = False

    # ------------------------------------------------------------------
    # Reference-counting context manager
    # ------------------------------------------------------------------

    @_check_types.do
    def __enter__(self):
        self._ref_count += 1

        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    @_check_types.do
    def Refresh(self, *_, **__) -> None:
        """
        Refreshes the canvas so all objects are redrawn.
        """

        if self._ref_count:
            return

        self.update()

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # ------------------------------------------------------------------

    @_check_types.do
    def initializeGL(self) -> None:
        """
        One-time GL setup (replaces _init_gl called from _on_paint).

        Qt guarantees the context is already current here.
        """

        GL.glClearColor(0.9600, 0.9568, 0.9372, 1.0)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
        GL.glDisable(GL.GL_DEPTH_TEST)

        if self._size is None:
            self._size = self.size()

        GL.glViewport(0, 0, self._size.width(), self._size.height())

        self._setup_projection()
        self._grid.set(self.config.grid.enabled)

    @_check_types.do
    def resizeGL(self, width: int, height: int) -> None:
        """
        Called by Qt on resize (replaces EVT_SIZE handler).

        Context is already current here.
        """

        self._size = QSize(width, height)
        GL.glViewport(0, 0, width, height)
        self._setup_projection()
        self.camera.invalidate_views()

    @_check_types.do
    def paintGL(self) -> None:
        """
        Render one frame (replaces EVT_PAINT / _on_paint).

        Context is already current here.

        Two rendering paths coexist while object types migrate from the
        legacy immediate-mode path one piece at a time (see
        objects.objects2d.base2d.Base2D): objects with a VBO
        (obj.obj2d.vbo is not None) render via _render_vbo_objects()'s
        schematic2d-shader pass; everything else still renders through its
        own render_gl() below, unchanged.
        """

        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        # TODO: update camera class so it functionally the same as the 3d camera.
        #       there can be different functions involved but it should largely
        #       work the same.
        self.camera._update_views()  # NOQA -- picks up glOrtho bounds set above

        self._grid.render(self.camera.distance)

        # TODO: add object culling here and pass the object list that is
        #  actually in view to the scene rendering function.

        objects = self.objects

        self._render_scene(objects)

        # Qt handles SwapBuffers automatically.

    def center_on_object(self, obj) -> None:
        # TODO: populate this function if the code is the same between the
        #       subclasses or leave it how it is and override the function in
        #       each subclass
        raise NotImplementedError

    def _render_scene(self, objects):
        # This function MUST be overridden by the subclass . this is the main
        # rendering function that gets called.

        raise NotImplementedError

    @_check_types.do
    def _setup_projection(self):
        """
        Execute the setup projection operation.
        """

        if self._size is None:
            return

        width, height = self._size.width(), self._size.height()
        if width == 0 or height == 0:
            return

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        x, y, _ = self.camera.position.as_float

        left = x - half_width
        right = x + half_width
        bottom = y - half_height
        top = y + half_height

        GL.glOrtho(left, right, bottom, top, -1.0, 1.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
