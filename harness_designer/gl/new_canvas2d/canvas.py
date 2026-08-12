# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Self

import numpy as np
from OpenGL import GL
import math
import ctypes
import weakref

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtOpenGLWidgets
from PySide6.QtCore import Signal
from PySide6.QtGui import QOpenGLContext

from .. import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from . import floor as _floor
from .. import culling as _culling
from .. import events as _events
from ... import logger as _logger
from ... import check_types as _check_types
from . import mouse_handler as _mouse_handler


if TYPE_CHECKING:
    from ... import ui as _ui


MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS


class CanvasEventFilter(QtCore.QObject):
    """Represent a canvas event filter in :mod:`harness_designer.gl.canvas3d.canvas`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas):
        """Initialise the :class:`CanvasEventFilter` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        """
        self.canvas = canvas  # Qt: install event filter instead of canvas.Bind()

        super().__init__()
        canvas.installEventFilter(self)

    @_check_types.do
    def eventFilter(self, obj, event):
        """Execute the event filter operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        :param event: Event object.
        :type event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if obj != self.canvas:
            return False

        t = event.type()

        # QtCore.QEvent.Type.ActionAdded
        # QtCore.QEvent.Type.ActionChanged
        # QtCore.QEvent.Type.ActionRemoved
        # QtCore.QEvent.Type.ActivationChange
        # QtCore.QEvent.Type.ApplicationActivate
        # QtCore.QEvent.Type.ApplicationActivated
        # QtCore.QEvent.Type.ApplicationDeactivate
        # QtCore.QEvent.Type.ApplicationFontChange
        # QtCore.QEvent.Type.ApplicationLayoutDirectionChange
        # QtCore.QEvent.Type.ApplicationPaletteChange
        # QtCore.QEvent.Type.ApplicationStateChange
        # QtCore.QEvent.Type.ApplicationWindowIconChange
        # QtCore.QEvent.Type.ChildAdded
        # QtCore.QEvent.Type.ChildPolished
        # QtCore.QEvent.Type.ChildRemoved
        # QtCore.QEvent.Type.ChildWindowAdded
        # QtCore.QEvent.Type.ChildWindowRemoved
        # QtCore.QEvent.Type.Clipboard
        # QtCore.QEvent.Type.Close
        # QtCore.QEvent.Type.CloseSoftwareInputPanel
        # QtCore.QEvent.Type.ContentsRectChange
        # QtCore.QEvent.Type.ContextMenu
        # QtCore.QEvent.Type.CursorChange
        # QtCore.QEvent.Type.DeferredDelete
        # QtCore.QEvent.Type.DevicePixelRatioChange
        # QtCore.QEvent.Type.DragEnter
        # QtCore.QEvent.Type.DragLeave
        # QtCore.QEvent.Type.DragMove
        # QtCore.QEvent.Type.Drop
        # QtCore.QEvent.Type.DynamicPropertyChange
        # QtCore.QEvent.Type.EnabledChange
        # QtCore.QEvent.Type.Enter
        # QtCore.QEvent.Type.EnterEditFocus
        # QtCore.QEvent.Type.EnterWhatsThisMode
        # QtCore.QEvent.Type.Expose
        # QtCore.QEvent.Type.FileOpen
        # QtCore.QEvent.Type.FocusIn
        # QtCore.QEvent.Type.FocusOut
        # QtCore.QEvent.Type.FocusAboutToChange
        # QtCore.QEvent.Type.FontChange
        # QtCore.QEvent.Type.Gesture
        # QtCore.QEvent.Type.GestureOverride
        # QtCore.QEvent.Type.GrabKeyboard
        # QtCore.QEvent.Type.GrabMouse
        # QtCore.QEvent.Type.GraphicsSceneContextMenu
        # QtCore.QEvent.Type.GraphicsSceneDragEnter
        # QtCore.QEvent.Type.GraphicsSceneDragLeave
        # QtCore.QEvent.Type.GraphicsSceneDragMove
        # QtCore.QEvent.Type.GraphicsSceneDrop
        # QtCore.QEvent.Type.GraphicsSceneHelp
        # QtCore.QEvent.Type.GraphicsSceneHoverEnter
        # QtCore.QEvent.Type.GraphicsSceneHoverLeave
        # QtCore.QEvent.Type.GraphicsSceneHoverMove
        # QtCore.QEvent.Type.GraphicsSceneMouseDoubleClick
        # QtCore.QEvent.Type.GraphicsSceneMouseMove
        # QtCore.QEvent.Type.GraphicsSceneMousePress
        # QtCore.QEvent.Type.GraphicsSceneMouseRelease
        # QtCore.QEvent.Type.GraphicsSceneMove
        # QtCore.QEvent.Type.GraphicsSceneResize
        # QtCore.QEvent.Type.GraphicsSceneWheel
        # QtCore.QEvent.Type.GraphicsSceneLeave
        # QtCore.QEvent.Type.Hide
        # QtCore.QEvent.Type.HideToParent
        # QtCore.QEvent.Type.HoverEnter
        # QtCore.QEvent.Type.HoverLeave
        # QtCore.QEvent.Type.HoverMove
        # QtCore.QEvent.Type.IconDrag
        # QtCore.QEvent.Type.IconTextChange
        # QtCore.QEvent.Type.InputMethod
        # QtCore.QEvent.Type.InputMethodQuery
        # QtCore.QEvent.Type.KeyboardLayoutChange
        # QtCore.QEvent.Type.KeyPress
        # QtCore.QEvent.Type.KeyRelease
        # QtCore.QEvent.Type.LanguageChange
        # QtCore.QEvent.Type.LayoutDirectionChange
        # QtCore.QEvent.Type.LayoutRequest
        # QtCore.QEvent.Type.Leave
        # QtCore.QEvent.Type.LeaveEditFocus
        # QtCore.QEvent.Type.LeaveWhatsThisMode
        # QtCore.QEvent.Type.LocaleChange
        # QtCore.QEvent.Type.NonClientAreaMouseButtonDblClick
        # QtCore.QEvent.Type.NonClientAreaMouseButtonPress
        # QtCore.QEvent.Type.NonClientAreaMouseButtonRelease
        # QtCore.QEvent.Type.NonClientAreaMouseMove
        # QtCore.QEvent.Type.MacSizeChange
        # QtCore.QEvent.Type.MetaCall
        # QtCore.QEvent.Type.ModifiedChange
        # QtCore.QEvent.Type.MouseButtonDblClick
        # QtCore.QEvent.Type.MouseButtonPress
        # QtCore.QEvent.Type.MouseButtonRelease
        # QtCore.QEvent.Type.MouseMove
        # QtCore.QEvent.Type.MouseTrackingChange
        # QtCore.QEvent.Type.Move
        # QtCore.QEvent.Type.NativeGesture
        # QtCore.QEvent.Type.OrientationChange
        # QtCore.QEvent.Type.Paint
        # QtCore.QEvent.Type.PaletteChange
        # QtCore.QEvent.Type.ParentAboutToChange
        # QtCore.QEvent.Type.ParentChange
        # QtCore.QEvent.Type.ParentWindowAboutToChange
        # QtCore.QEvent.Type.ParentWindowChange
        # QtCore.QEvent.Type.PlatformPanel
        # QtCore.QEvent.Type.PlatformSurface
        # QtCore.QEvent.Type.Polish
        # QtCore.QEvent.Type.PolishRequest
        # QtCore.QEvent.Type.QueryWhatsThis
        # QtCore.QEvent.Type.Quit
        # QtCore.QEvent.Type.ReadOnlyChange
        # QtCore.QEvent.Type.RequestSoftwareInputPanel
        # QtCore.QEvent.Type.Resize
        # QtCore.QEvent.Type.ScrollPrepare
        # QtCore.QEvent.Type.Scroll
        # QtCore.QEvent.Type.Shortcut
        # QtCore.QEvent.Type.ShortcutOverride
        # QtCore.QEvent.Type.Show
        # QtCore.QEvent.Type.ShowToParent
        # QtCore.QEvent.Type.SockAct
        # QtCore.QEvent.Type.StateMachineSignal
        # QtCore.QEvent.Type.StateMachineWrapped
        # QtCore.QEvent.Type.StatusTip
        # QtCore.QEvent.Type.StyleChange
        # QtCore.QEvent.Type.TabletMove
        # QtCore.QEvent.Type.TabletPress
        # QtCore.QEvent.Type.TabletRelease
        # QtCore.QEvent.Type.TabletEnterProximity
        # QtCore.QEvent.Type.TabletLeaveProximity
        # QtCore.QEvent.Type.TabletTrackingChange
        # QtCore.QEvent.Type.ThreadChange
        # QtCore.QEvent.Type.Timer
        # QtCore.QEvent.Type.ToolBarChange
        # QtCore.QEvent.Type.ToolTip
        # QtCore.QEvent.Type.ToolTipChange
        # QtCore.QEvent.Type.TouchBegin
        # QtCore.QEvent.Type.TouchCancel
        # QtCore.QEvent.Type.TouchEnd
        # QtCore.QEvent.Type.TouchUpdate
        # QtCore.QEvent.Type.UngrabKeyboard
        # QtCore.QEvent.Type.UngrabMouse
        # QtCore.QEvent.Type.UpdateLater
        # QtCore.QEvent.Type.UpdateRequest
        # QtCore.QEvent.Type.WhatsThis
        # QtCore.QEvent.Type.WhatsThisClicked
        # QtCore.QEvent.Type.Wheel
        # QtCore.QEvent.Type.WinEventAct
        # QtCore.QEvent.Type.WindowActivate
        # QtCore.QEvent.Type.WindowBlocked
        # QtCore.QEvent.Type.WindowDeactivate
        # QtCore.QEvent.Type.WindowIconChange
        # QtCore.QEvent.Type.WindowStateChange
        # QtCore.QEvent.Type.WindowTitleChange
        # QtCore.QEvent.Type.WindowUnblocked
        # QtCore.QEvent.Type.WinIdChange
        # QtCore.QEvent.Type.ZOrderChange
        # QtCore.QEvent.Type.SafeAreaMarginsChange

        if t in (
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QEvent.Type.MouseButtonDblClick,
            QtCore.QEvent.Type.MouseMove,
            QtCore.QEvent.Type.Wheel
        ):
            self.canvas._mouse_handler.handle_event(event)  # NOQA

        elif t in (
            QtCore.QEvent.Type.KeyPress,
            QtCore.QEvent.Type.KeyRelease
        ):
            self.canvas._key_handler.handle_event(event)  # NOQA

        elif t == QtCore.QEvent.Type.FocusOut:
            # The canvas loses keyboard focus while a movement key is held
            # (a context menu or modal dialog opens, another dock gets
            # clicked, etc.) -- the KeyRelease that would normally clear
            # that key goes to whichever widget has focus now, never to
            # this filter, so without this the key stays "down" forever
            # and the camera keeps moving on its own after it's released.
            self.canvas._key_handler.clear_keys()  # NOQA

        # Mouse capture lost: Qt sends QEvent.Type.MouseButtonRelease with no
        # button held when the grab is broken externally.  For explicit
        # capture-lost notification we use QWidget.mouseGrabber() == None
        # after a grab was active.  The canvas calls this directly when
        # needed — see Canvas.changeEvent override (not required here).
        return super().eventFilter(obj, event)


class Canvas(QtOpenGLWidgets.QOpenGLWidget):
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

    gl_camera_zoom = Signal(object)
    gl_camera_orbit = Signal(object)
    gl_camera_walk = Signal(object)
    gl_camera_truckpedistal = Signal(object)
    gl_camera_rotate = Signal(object)
    gl_camera_reset = Signal(object)

    # mouse handler gets set by the subclass after calling super
    _mouse_handler: _mouse_handler.MouseHandler = None

    @_check_types.do
    def __init__(self, parent, mainframe: "_ui.MainFrame", config, size: QtCore.QSize = None):
        """Initialise the :class:`Canvas` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor3d`
        :param size: Value for ``size``.
        :type size: :class:`QtCore.QSize`
        """

        QtOpenGLWidgets.QOpenGLWidget.__init__(self, parent)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.mainframe = mainframe

        self.config = config
        self._mode = None

        from .. import context as _context
        from . import camera as _camera

        # Create the GLContext wrapper for this widget.
        # Use it ONLY outside of initializeGL / resizeGL / paintGL —
        # Qt already makes the context current before calling those.
        self.context = _context.GLContext(self)

        self._init = False
        self.camera = _camera.Camera(self)

        self._faces_program = None
        self._edges_program = None
        self._vertices_program = None
        self._floor_program = None

        self.floor: _floor.Floor = None
        self._last_culled = []
        self._object_refs = []
        self._objects_in_view = []
        self._object_addr_mapping = {}

        self._object_data = [[], [], [], [], [], [], [], [], [], []]

        self.size = None

        self._selected = None
        self._objects = []
        self._ref_count = 0

        from . import key_handler as _key_handler
        from . import scene_light as _scene_light

        self._key_handler = _key_handler.KeyHandler(self)
        self._scene_light = _scene_light.SceneLight(self)

        self._event_filter = CanvasEventFilter(self)

        if size is not None:
            self.resize(size)

        font = self.font()
        font.setPointSize(15)
        self.setFont(font)

    @property
    @_check_types.do
    def objects_in_view(self) -> list:
        """Return the objects in view.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list
        """
        return self._objects_in_view

    @_check_types.do
    def set_mode(self, mode: int) -> None:
        """Set the mode.

        UNKNOWN details are inferred from the callable name and signature.

        :param mode: Value for ``mode``.
        :type mode: int
        """
        self._mode = mode

    @_check_types.do
    def set_selected(self, obj):
        """
        Set the selected object.
        """

        self._selected = obj

    @_check_types.do
    def get_selected(self):
        """
        Return the selected onject.
        """

        return self._selected

    @_check_types.do
    def add_object(self, obj):
        """
        Add an object.
        """

        found_container = self._object_data[0]
        container_len = 9999999999

        for container in self._object_data:
            if len(container) < container_len:
                found_container = container
                container_len = len(container)

        aabb_min, aabb_max = obj.obj3d.aabb
        pos = obj.obj3d.position.as_numpy
        is_opaque = obj.obj3d.is_opaque

        obj_ref = weakref.ref(obj, self.__remove_obj_ref)
        obj_address = id(obj_ref)

        self._object_refs.append(obj_ref)
        self._object_addr_mapping[obj] = obj_address

        found_container.append([aabb_min, aabb_max, pos, is_opaque, obj_address])
        self._objects.append(obj)

    @_check_types.do
    def __remove_obj_ref(self, ref):
        """
        Remove the obj ref.
        """

        try:
            self._object_refs.remove(ref)
        except ValueError:
            pass

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.
        """

        try:
            self._objects.remove(obj)
        except ValueError:
            pass

        try:
            self._objects_in_view.remove(obj)
        except ValueError:
            pass

        if obj in self._object_addr_mapping:
            obj_address = self._object_addr_mapping.pop(obj)
            for container in self._object_data:
                for i, line in enumerate(container):
                    if line[-1] == obj_address:
                        container.pop(i)
                        break
                else:
                    continue
                break

        self.update()  # Qt: schedules a repaint (≈ wx Refresh)

    @_check_types.do
    def clear(self) -> None:
        """
        Drop every scene object in bulk, without touching the database.

        Used when tearing down the current project so a different one can
        load in its place (see ``ui.mainframe.MainFrame.unload``) --
        resets the same tracking structures :meth:`remove_object` does,
        but in one shot instead of one O(n) scan per object, since a
        project can hold thousands of objects.
        """
        self._object_refs = []
        self._objects_in_view = []
        self._object_addr_mapping = {}
        self._object_data = [[], [], [], [], [], [], [], [], [], []]
        self._objects = []
        self._selected = None
        self.update()

    @_check_types.do
    def __enter__(self) -> Self:
        self._ref_count += 1
        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    @_check_types.do
    def Refresh(self, *_, **__):
        if self._ref_count:
            return

        self.update()

    @_debug.logfunc
    @_check_types.do
    def TruckPedestal(self, dx: float, dy: float) -> None:
        """
        Execute the truck pedestal operation.

        :param dx: Value for ``dx``.
        :type dx: float

        :param dy: Value for ``dy``.
        :type dy: float
        """

        if self.config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx
        if self.config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy
        sens = self.config.truck_pedestal.sensitivity
        self.camera.TruckPedestal(dx * sens, dy * sens, self.config.truck_pedestal.speed)

    @_debug.logfunc
    @_check_types.do
    def Zoom(self, dx: float, _=None):
        """
        Execute the zoom operation.
        """

        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle overrides
    # wx: __init__ + EVT_PAINT + EVT_SIZE + EVT_ERASE_BACKGROUND
    # Qt: initializeGL + paintGL + resizeGL  (SwapBuffers implicit)
    # ------------------------------------------------------------------

    @_check_types.do
    def _ortho_bounds(self) -> tuple[float, float, float, float]:
        """Return ``(left, right, bottom, top)`` for this frame's
        ``glOrtho`` call, sized from the camera's current zoom level
        (``camera.focal_distance``) and the current viewport pixel size
        (``self.size``).

        ``camera.Set()``'s ``gluLookAt`` (MODELVIEW) already centers the
        view on the camera's own ``focal_position``, so these bounds are
        always symmetric around 0 -- unlike
        ``gl.canvas2d.canvas.Canvas._setup_projection``'s older,
        no-MODELVIEW convention, which baked the focal position directly
        into the ``glOrtho`` bounds instead.

        Same ``distance / 1000.0`` world-per-pixel convention
        ``gl.canvas2d.camera.Camera`` uses, so mouse-wheel zoom feels the
        same across both the old and new 2D canvases.

        :returns: ``(left, right, bottom, top)``.
        """
        if self.size:
            width, height = self.size
        else:
            width, height = self.width(), self.height()

        world_per_pixel = self.camera.focal_distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        return -half_width, half_width, -half_height, half_height

    @_check_types.do
    def initializeGL(self):
        """Called once by Qt after the GL context is created.
        Qt guarantees the context is already current here — no makeCurrent needed."""

        try:
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glClearColor(*self.config.background_color)

            self._faces_program = _shaders.compile_faces_program()
            self._edges_program = _shaders.compile_edges_program()
            self._vertices_program = _shaders.compile_vertices_program()
            self._floor_program = _shaders.compile_grid2d_program()

            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            # Initialize OpenGL matrix stacks BEFORE doing anything else
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()

            # Use the virtual size recorded in resizeGL (first call), not the
            # current widget geometry, so the aspect ratio matches the virtual
            # canvas — not the (possibly different) container size.
            vw = getattr(self, "_virtual_w", None) or self.width()
            vh = getattr(self, "_virtual_h", None) or self.height()
            
            # Ensure we have valid dimensions (must be > 0)
            if vw <= 0 or vh <= 0:
                _logger.warning(f"  ! WARNING: Invalid viewport dimensions ({vw}x{vh}), using fallback 1920x1080")
                vw = 1920
                vh = 1080

            GL.glViewport(0, 0, vw, vh)
            self.size = (vw, vh)

            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            left, right, bottom, top = self._ortho_bounds()
            GL.glOrtho(left, right, bottom, top, 0.1, 1000.0)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()

            self.camera.Set()

            self._init = True  # viewport is live; notify_virtual_size_changed may update it
            self.floor = _floor.Floor(self, self._floor_program)

            self.set_draw_grid(self.config.floor.enable)

            self.update()
            self.repaint()

        except Exception as err:  # NOQA
            _logger.traceback(err, 'initializeGL')
            raise

    @_check_types.do
    def notify_virtual_size_changed(self, width: int, height: int) -> None:
        """
        Called by Canvas3D.set_virtual_size() (and on first initialisation)
        to update the GL viewport and camera projection for a new virtual
        canvas size.

        This is the Qt equivalent of wx EVT_SIZE triggered by SetVirtualSize.
        Unlike resizeGL — which Qt calls automatically whenever the widget's
        widget geometry changes — this method is only called when the *render*
        size genuinely changes, so the aspect ratio is never distorted by a
        passive parent-panel resize.
        """
        dpr = self.devicePixelRatio()
        w = int(width * dpr)
        h = int(height * dpr)
        self._virtual_w = w  # NOQA
        self._virtual_h = h  # NOQA
        self.size = (w, h)

        with self.context:
            GL.glViewport(0, 0, w, h)

        self.update()

    @_check_types.do
    def resizeGL(self, width: int, height: int):
        """
        Called by Qt whenever the *widget geometry* changes.

        wx behaviour: the canvas had a fixed virtual size set via
        SetVirtualSize().  Resizing the surrounding panel did NOT fire an
        EVT_SIZE on the canvas and therefore never changed the GL viewport.

        Qt equivalent: resizeGL fires for every geometry change, including
        passive ones caused by layout managers.  We ignore those here —
        viewport updates only happen through notify_virtual_size_changed(),
        which is triggered only when the virtual size is intentionally changed.

        The only exception is the very first call (before _init is set),
        which we use to record the initial size so the viewport is set up
        correctly when initializeGL runs.
        """
        if not self._init:
            # Record initial size; initializeGL will apply the viewport.
            dpr = self.devicePixelRatio()
            self._virtual_w = int(width * dpr)  # NOQA
            self._virtual_h = int(height * dpr)  # NOQA
            self.size = (self._virtual_w, self._virtual_h)
        # else: ignore — virtual size is managed by notify_virtual_size_changed

    @_check_types.do
    def paintGL(self):
        """
        Called by Qt to render a frame. Context is already current here.
        """

        self._on_draw()

        # Qt handles buffer swap automatically — no SwapBuffers() call needed.

    # ------------------------------------------------------------------
    # Internal GL helpers (unchanged rendering logic)
    # ------------------------------------------------------------------

    @_check_types.do
    def set_draw_grid(self, flag):
        """Set the draw grid.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: UNKNOWN
        """
        try:
            self.floor.set(flag)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'set floor error')

    @_debug.logfunc
    @_check_types.do
    def _draw_scene(self, objects):
        """
        Draw the scene.

        This function MUST be overridden by the subclass
        """

        raise NotImplementedError
        # projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        # view_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        #
        # # ---------- Faces program
        # GL.glUseProgram(self._faces_program)
        #
        # # ---------- Faces program variable locations
        # view_position = GL.glGetUniformLocation(
        #     self._faces_program, 'viewPosition')
        #
        # projection = GL.glGetUniformLocation(
        #     self._faces_program, 'projection')
        #
        # view = GL.glGetUniformLocation(
        #     self._faces_program, 'view')
        #
        # floor_y = GL.glGetUniformLocation(
        #     self._faces_program, 'floorY')
        #
        # object_has_reflection = GL.glGetUniformLocation(
        #     self._faces_program, 'objectHasReflection')
        #
        # # ---------- Faces program set variables
        # GL.glUniform3fv(
        #     view_position, 1, self.camera.position.as_numpy)
        #
        # GL.glUniformMatrix4fv(
        #     projection, 1, GL.GL_FALSE, projection_matrix)
        #
        # GL.glUniformMatrix4fv(
        #     view, 1, GL.GL_FALSE, view_matrix)
        #
        # GL.glUniform1f(
        #     floor_y, self.config.floor.ground_height)
        #
        # GL.glUniform1i(
        #     object_has_reflection,
        #     int(self.config.floor.reflections.enable and
        #         self.config.floor.enable_floor_lock))
        #
        # # ---------- Edges program
        # GL.glUseProgram(self._edges_program)
        #
        # # ---------- Edges program variable locations
        # projection = GL.glGetUniformLocation(
        #     self._edges_program, 'projection')
        #
        # view = GL.glGetUniformLocation(
        #     self._edges_program, 'view')
        #
        # # ---------- Edges program set variables
        # GL.glUniformMatrix4fv(
        #     projection, 1, GL.GL_FALSE, projection_matrix)
        #
        # GL.glUniformMatrix4fv(view, 1, GL.GL_FALSE, view_matrix)
        #
        # # ---------- Vertices program
        # GL.glUseProgram(self._vertices_program)
        #
        # # ---------- Vertices program variable locations
        # projection = GL.glGetUniformLocation(
        #     self._vertices_program, 'projection')
        #
        # view = GL.glGetUniformLocation(
        #     self._vertices_program, 'view')
        #
        # # ---------- Vertices program set variables
        # GL.glUniformMatrix4fv(
        #     projection, 1, GL.GL_FALSE, projection_matrix)
        #
        # GL.glUniformMatrix4fv(
        #     view, 1, GL.GL_FALSE, view_matrix)
        #
        # # ---------- Faces program rendering
        # GL.glUseProgram(self._faces_program)
        #
        # # ---------- Faces program set lighting
        # try:
        #     self._scene_light.set(self._faces_program)
        # except Exception as err:  # NOQA
        #     _logger.traceback(err, 'scene light error')
        #
        # removed_objects = []
        # objects_in_view = []
        #
        # for row in obj_data:
        #     try:
        #         ref_address = row[-1]
        #         obj_ref = ctypes.cast(ref_address, ctypes.py_object).value
        #         obj = obj_ref()
        #
        #         if obj is None:
        #             try:
        #                 self._object_refs.remove(obj_ref)
        #             except ValueError:
        #                 pass
        #             removed_objects.append(row)
        #             continue
        #
        #         objects_in_view.append(obj)
        #
        #         # A selected, translucent object is deferred to a later
        #         # pass (see _on_draw, right after this method returns) so
        #         # it always renders AFTER every opaque object in the scene
        #         # regardless of where it falls in this loop's arbitrary
        #         # bucket order -- otherwise whichever opaque objects (e.g.
        #         # a housing's own interior terminals/wires) happen to be
        #         # drawn after it here would get fully overwritten instead
        #         # of showing through it.
        #         if obj is self._selected and not obj.obj3d.is_opaque:
        #             continue
        #
        #         obj.obj3d.render(self._faces_program, self._edges_program, self._vertices_program)
        #     except Exception as err:  # NOQA
        #         _logger.traceback(err, 'object render error')
        #
        # GL.glUseProgram(0)
        # self._objects_in_view = objects_in_view
        #
        # for row in removed_objects:
        #     try:
        #         for container in self._object_data:
        #             try:
        #                 container.remove(row)
        #                 break
        #             except ValueError:
        #                 continue
        #     except Exception as err:  # NOQA
        #         _logger.traceback(err, 'object render removal error')

    @_debug.logfunc
    @_check_types.do
    def _on_draw(self):
        """
        Handle the draw event.

        Generic rendering setup.
        Sets up OpenGL and the camera to render the scene and culls the stored
        objects to be rendered. those culled objects get passed to the
        _draw_scene function to be handled by the subclass.
        """

        f_size = self.config.floor.grid.size ** 2

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        GL.glLineWidth(2.0)

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        left, right, bottom, top = self._ortho_bounds()
        GL.glOrtho(left, right, bottom, top, 0.1, float(math.sqrt(f_size * f_size)))

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        try:
            self.camera.Set()
        except Exception as err:  # NOQA
            _logger.traceback(err, 'camera set error')

        try:
            objs = _culling.cull(
                self._object_data, self.camera.frustum_normals,
                self.camera.frustum_distances, self.camera.position.as_numpy)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'culling error')
            return

        self._draw_scene(objs)

        try:
            self.floor.render(self._floor_program)
        except:  # NOQA
            import traceback
            traceback.print_exc()
            raise

        # Qt handles SwapBuffers automatically — removed.

    @_check_types.do
    def take_snapshot(self) -> QtGui.QImage:
        """Execute the take snapshot operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QtGui.QImage`
        """
        # grabFramebuffer() renders a frame and resolves the (multisampled)
        # widget FBO into a plain image — raw glReadPixels would be invalid
        # against the MSAA framebuffer.
        return self.grabFramebuffer().convertToFormat(
            QtGui.QImage.Format.Format_RGB888)

    @_check_types.do
    def cleanup(self):
        """Clean up GL resources before widget destruction."""
        # Currently no explicit cleanup needed - shaders/programs are
        # automatically cleaned up by Qt when the context is destroyed
        pass
