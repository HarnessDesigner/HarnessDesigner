# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Self, TYPE_CHECKING

from OpenGL import GL
import ctypes
import weakref

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtOpenGLWidgets

from .. import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from .. import culling as _culling
from ... import logger as _logger
from ... import check_types as _check_types
from . import camera_base as _camera_base
from . import floor_base as _floor_base
from . import key_handler as _key_handler
from . import scene_light as _scene_light
from . import mouse_handler_base as _mouse_handler_base


if TYPE_CHECKING:
    from ... import ui as _ui

MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS

_debug_config = _config.Config.debug.rendering3d


class CanvasEventFilter(QtCore.QObject):
    """Represent a canvas event filter in :mod:`harness_designer.gl.canvas3d.canvas`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "CanvasBase"):
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


class CanvasBase(QtOpenGLWidgets.QOpenGLWidget):
    """
    3D GL Engine — wx.glcanvas.GLCanvas → QOpenGLWidget

    All PyOpenGL rendering code (shaders, VBOs, materials, camera) is
    completely unchanged.  Only the canvas lifecycle changes:

        wx                          Qt
        ──────────────────────────  ────────────────────────────────────
        GLCanvas.__init__           QOpenGLWidget.__init__
        glcanvas.GLContext          managed by QOpenGLWidget internally
        SetCurrent(context)         makeCurrent()  (in GLContext.acquire)
        SwapBuffers()               automatically done by QOpenGLWidget
        EVT_PAINT → _on_paint       paintGL() override
        EVT_SIZE  → _on_size        resizeGL(w, h) override
        EVT_ERASE_BACKGROUND        not needed
        wx.PaintDC(self)            not needed
        wx.CallAfter(fn)            QTimer.singleShot(0, fn)
        GetSize() → wx.Size         self.width(), self.height()
        GetContentScaleFactor()     self.devicePixelRatio()

    Signals replace wx custom events (EVT_GL_*).  Each signal carries a
    single GL event data object (GLEvent / GLObjectEvent / GLKeyEvent /
    GLCaptureLostEvent) — all wx-free plain Python objects.

    The mouse/key handlers and all object-management code are unchanged.
    """

    # ------------------------------------------------------------------
    # Signals — replace wx EVT_GL_* custom events
    # Each carries a single GL event data object.
    # ------------------------------------------------------------------

    gl_object_selected = QtCore.Signal(object)
    gl_object_unselected = QtCore.Signal(object)
    gl_object_activated = QtCore.Signal(object)
    gl_object_right_click = QtCore.Signal(object)
    gl_object_right_dclick = QtCore.Signal(object)
    gl_object_middle_click = QtCore.Signal(object)
    gl_object_middle_dclick = QtCore.Signal(object)
    gl_object_aux1_click = QtCore.Signal(object)
    gl_object_aux1_dclick = QtCore.Signal(object)
    gl_object_aux2_click = QtCore.Signal(object)
    gl_object_aux2_dclick = QtCore.Signal(object)
    gl_object_drag = QtCore.Signal(object)
    gl_key_down = QtCore.Signal(object)
    gl_key_up = QtCore.Signal(object)
    gl_mouse_move = QtCore.Signal(object)
    gl_left_down = QtCore.Signal(object)
    gl_left_up = QtCore.Signal(object)
    gl_left_dclick = QtCore.Signal(object)
    gl_right_down = QtCore.Signal(object)
    gl_right_up = QtCore.Signal(object)
    gl_right_dclick = QtCore.Signal(object)
    gl_middle_down = QtCore.Signal(object)
    gl_middle_up = QtCore.Signal(object)
    gl_middle_dclick = QtCore.Signal(object)
    gl_aux1_down = QtCore.Signal(object)
    gl_aux1_up = QtCore.Signal(object)
    gl_aux1_dclick = QtCore.Signal(object)
    gl_aux2_down = QtCore.Signal(object)
    gl_aux2_up = QtCore.Signal(object)
    gl_aux2_dclick = QtCore.Signal(object)
    gl_capture_lost = QtCore.Signal(object)

    gl_camera_zoom = QtCore.Signal(object)
    gl_camera_orbit = QtCore.Signal(object)
    gl_camera_walk = QtCore.Signal(object)
    gl_camera_truckpedistal = QtCore.Signal(object)
    gl_camera_rotate = QtCore.Signal(object)
    gl_camera_reset = QtCore.Signal(object)
    gl_camera_dolly = QtCore.Signal(object)

    # These next few attributes need to be created after super() is called
    _mouse_handler: _mouse_handler_base.MouseHandlerBase = None
    camera: _camera_base.CameraBase = None

    # This attribute needs to be created in an overrided initializeGL function
    # created before calling super().initializeGL
    _floor: _floor_base.FloorBase = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", config, size: QtCore.QSize = None):
        """
        Initialise the :class:`CanvasBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Parent object.
        :type mainframe: :class:`_ui.MainFrame`

        :param config: Value for ``config``.
        :type config: UNKNOWN

        :param size: Value for ``size``.
        :type size: :class:`QtCore.QSize`
        """

        super().__init__(None)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Ensure depth buffering and double-buffering are active.
        # The model_preview canvas sets this explicitly; the main 3D canvas must too.
        # from PySide6.QtGui import QSurfaceFormat
        # fmt = QSurfaceFormat()
        # fmt.setDepthBufferSize(24)
        # fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        # self.setFormat(fmt)

        self.mainframe = mainframe

        self.config = config
        self._mode = None

        from .. import context as _context

        # Create the GLContext wrapper for this widget.
        # Use it ONLY outside of initializeGL / resizeGL / paintGL —
        # Qt already makes the context current before calling those.
        self.context = _context.GLContext(self)

        self._init = False

        self._shaders = None

        self._last_culled = []
        self._object_refs = []
        self._objects_in_view = []
        self._object_addr_mapping = {}

        self._object_data = [[], [], [], [], [], [], [], [], [], []]

        self.size = None

        self._selected = None
        self._objects = []
        self._ref_count = 0

        self._event_filter = CanvasEventFilter(self)

        if size is not None:
            self.resize(size)

        font = self.font()
        font.setPointSize(15)
        self.setFont(font)

        # Deferred (not module-level) import: mouse_handler transitively
        # imports objects.housing -> ... -> ui.dialogs.housing_editor ->
        # gl.canvas_3d -> needs canvas_base.CanvasBase already defined --
        # a module-level import here creates a circular import that fails
        # with "partially initialized module ... has no attribute
        # 'CanvasBase'" the first time anything imports gl.canvas_base
        # before gl.canvas_3d has. By construction time (__init__ actually
        # running, not just the class being defined) the whole module
        # graph has already settled, so the cycle doesn't apply here.
        self._key_handler = _key_handler.KeyHandler(self)
        self._scene_light: _scene_light.SceneLight = None

    # ------------------------------------------------------------------
    # Properties / mode
    # -----------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Object management (unchanged from wx version)
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
        """
        Add an object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
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

        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """

        try:
            self._object_refs.remove(ref)
        except ValueError:
            pass

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
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

    # ------------------------------------------------------------------
    # Reference-counting context manager (unchanged)
    # ------------------------------------------------------------------

    @_check_types.do
    def __enter__(self) -> Self:
        self._ref_count += 1
        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    @_check_types.do
    def Refresh(self, *_, **__):
        """
        wx-compatible name; delegates to Qt update().
        """

        if self._ref_count:
            return

        self.update()

    # ------------------------------------------------------------------
    # Camera movement API (unchanged — called by mouse/key handlers)
    # ------------------------------------------------------------------

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

        if self.config.input.truck_pedestal.mouse is None:
            return

        if self.config.input.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.input.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.input.truck_pedestal.sensitivity
        self.camera.TruckPedestal(dx * sens, dy * sens, self.config.truck_pedestal.speed)

    @_debug.logfunc
    @_check_types.do
    def Zoom(self, dx: float, _=None):
        """
        Execute the zoom operation.

        :param dx: Value for ``dx``.
        :type dx: float

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        if self.config.input.zoom.sensitivity is None:
            return

        dx *= self.config.input.zoom.sensitivity
        self.camera.Zoom(dx)

    def Dolly(self, distance: float) -> None:
        self.camera.Dolly(distance)

    @_check_types.do
    def Rotate(self, dx: float, dy: float) -> None:
        """Execute the rotate operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: float
        :param dy: Value for ``dy``.
        :type dy: float
        """

        sens = self.config.input.rotate.sensitivity
        if sens is None:
            return

        self.camera.Rotate(dx * sens, dy * sens)

    @_debug.logfunc
    @_check_types.do
    def Walk(self, dx: float, dy: float) -> None:
        """
        Execute the walk operation.

        :param dx: Value for ``dx``.
        :type dx: float

        :param dy: Value for ``dy``.
        :type dy: float
        """

        if dy == 0.0:
            self.PanTilt(dx * 6.0, 0.0)
            return

        sens = self.config.input.walk.sensitivity
        self.camera.Walk(dx * sens, dy * sens, self.config.input.walk.speed)
        self.PanTilt(dx * 2.0, 0.0)

    @_debug.logfunc
    @_check_types.do
    def PanTilt(self, dx: float, dy: float) -> None:
        """Execute the pan tilt operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: float

        :param dy: Value for ``dy``.
        :type dy: float
        """

        sens = self.config.input.pan_tilt.sensitivity
        if sens is None:
            return

        self.camera.PanTilt(dx * sens, dy * sens)

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle overrides
    # wx: __init__ + EVT_PAINT + EVT_SIZE + EVT_ERASE_BACKGROUND
    # Qt: initializeGL + paintGL + resizeGL  (SwapBuffers implicit)
    # ------------------------------------------------------------------

    @_check_types.do
    def initializeGL(self):
        """Called once by Qt after the GL context is created.
        Qt guarantees the context is already current here — no makeCurrent needed."""

        try:
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glEnable(GL.GL_LINE_SMOOTH)
            GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
            GL.glClearColor(*self.config.background_color)

            self._shaders = _shaders.ShaderProgram()

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

            self._init = True  # viewport is live; notify_virtual_size_changed may update it

            self._scene_light = _scene_light.SceneLight(self)
            self.set_draw_floor(self.config.floor.enable)

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
    def set_draw_floor(self, flag: bool):
        """
        Set the draw grid.

        :param flag: Value for ``flag``.
        :type flag: bool
        """

        try:
            self._floor.set(flag)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'set floor error')

    def _set_shader_programs(self):
        # Camera's own locally-computed matrices (row-major, for
        # matrix @ column_vector) -- transpose=GL_TRUE converts them to
        # the column-major layout the shaders expect, instead of reading
        # GL_PROJECTION_MATRIX/GL_MODELVIEW_MATRIX back off the legacy
        # fixed-function matrix stack.
        projection_matrix = self.camera.projection
        view_matrix = self.camera.modelview

        has_reflection = int(self.config.floor.reflections.enable and
                             self.config.floor.enable_floor_lock)

        # ---------- Faces program
        with self._shaders.faces:
            self._shaders.faces.view_position = self.camera.position.as_numpy
            self._shaders.faces.projection = projection_matrix
            self._shaders.faces.view = view_matrix
            self._shaders.faces.floor_y = self.config.floor.ground_height
            self._shaders.faces.has_reflection = has_reflection

        # ---------- Edges program
        with self._shaders.edges:
            self._shaders.edges.projection = projection_matrix
            self._shaders.edges.view = view_matrix

        # ---------- Vertices program
        with self._shaders.vertices:
            self._shaders.vertices.projection = projection_matrix
            self._shaders.vertices.view = view_matrix

    @_debug.logfunc
    @_check_types.do
    def _draw_scene(self, obj_data):
        removed_objects = []
        objects_in_view = []

        for row in obj_data:
            try:
                ref_address = row[-1]
                obj_ref = ctypes.cast(ref_address, ctypes.py_object).value
                obj = obj_ref()

                if obj is None:
                    try:
                        self._object_refs.remove(obj_ref)
                    except ValueError:
                        pass

                    removed_objects.append(row)
                    continue

                objects_in_view.append(obj)

                # A selected, translucent object is deferred to a later
                # pass (see _on_draw, right after this method returns) so
                # it always renders AFTER every opaque object in the scene
                # regardless of where it falls in this loop's arbitrary
                # bucket order -- otherwise whichever opaque objects (e.g.
                # a housing's own interior terminals/wires) happen to be
                # drawn after it here would get fully overwritten instead
                # of showing through it.
                view_obj = self._get_view_object(obj)
                if obj is self._selected and not view_obj.is_opaque:
                    continue

                view_obj.render(self._shaders)

            except Exception as err:  # NOQA
                _logger.traceback(err, 'object render error')

        # Deferred full-color pass for the selected, translucent object --
        # see the matching "continue" in _draw_scene's own object loop,
        # which skips it there specifically so it always renders here,
        # after every opaque object in the scene already has its own
        # color+depth in the buffers. Depth writes are disabled for this
        # one render call so it still can't block whatever draws after it
        # (the depth-only pass below, the floor) -- it only ever reads the
        # depth buffer (correct occlusion against anything genuinely in
        # front of it, e.g. another housing between it and the camera)
        # and blends its own color on top of whatever's already there
        # (a housing's own interior terminals/wires, for instance)
        # instead of unconditionally overwriting them.
        #
        # This whole block runs once per frame, after the object loop
        # above has finished -- it must NOT sit inside that loop (it did,
        # for a long time, nested one level too deep): self._selected
        # doesn't depend on the loop variable at all, so running it once
        # per row in obj_data re-rendered/re-blended the selected object's
        # translucent shell and its debug overlay once per OTHER object in
        # the scene, compounding into exactly the over-darkened "muted"
        # look reported earlier.
        if self._selected is not None:
            view_obj = self._get_view_object(self._selected)

            if not view_obj.is_opaque:
                GL.glDepthMask(GL.GL_FALSE)

                try:
                    view_obj.render(self._shaders)
                except Exception as err:  # NOQA
                    _logger.traceback(
                        err, 'selected object deferred render error')

                GL.glDepthMask(GL.GL_TRUE)

                # Supplemental depth-only pass for selected (semi-transparent) objects.
                #
                # Transparent outer shells render with glDepthMask(FALSE) so interior
                # opaque parts remain visible through them.  That leaves 1.0 (background)
                # in the depth buffer at the shell's screen position, which lets the floor
                # pass the depth test and draw over the selected object.
                #
                # Fix: before the floor renders, write the outer-shell depth for each
                # selected object using GL_LESS with no colour output.  The floor then
                # fails the depth test at those positions and does not occlude the object.
                # Reflections are disabled for this pass so only above-floor geometry
                # contributes depth (reflections are deeper than the floor anyway, but
                # excluding them keeps the depth buffer clean).
                GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE,
                               GL.GL_FALSE, GL.GL_FALSE)

                GL.glDepthMask(GL.GL_TRUE)
                GL.glDepthFunc(GL.GL_LESS)

                with self._shaders.faces:
                    self._shaders.faces.has_reflection = 0

                try:
                    view_obj.render(self._shaders)
                except Exception as err:  # NOQA
                    _logger.traceback(
                        err, 'selected object render error')

                # Restore reflection uniform and colour mask before floor render.
                has_reflection = int(self.config.floor.reflections.enable and
                                     self.config.floor.enable_floor_lock)

                with self._shaders.faces:
                    self._shaders.faces.has_reflection = has_reflection

                GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE,
                               GL.GL_TRUE, GL.GL_TRUE)

        self._objects_in_view = objects_in_view

        for row in removed_objects:
            try:
                for container in self._object_data:
                    try:
                        container.remove(row)
                        break
                    except ValueError:
                        continue

            except Exception as err:  # NOQA
                _logger.traceback(err, 'object render removal error')

    @staticmethod
    def _get_view_object(obj):
        raise NotImplementedError

    def _set_view(self):
        raise NotImplementedError

    def _render_floor_before(self):
        pass

    def _render_floor_after(self):
        pass

    @_debug.logfunc
    @_check_types.do
    def _on_draw(self):
        # Every real frame must clear both buffers unconditionally, not
        # just when _set_view() actually rebuilds the projection --
        # schematic/pegboard's own _set_view() is dirty-gated (skips on
        # most frames, only rebuilding when the camera actually moved),
        # so a clear that only lived there left the previous frame's
        # dots/geometry on screen every time nothing but the view itself
        # changed, and the two blended into visible trailing/ghosting as
        # the camera panned. canvas_3d's own _set_view() already clears
        # unconditionally every call, so this is a harmless redundant
        # extra clear there, not a behavior change.
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        self.camera.set()
        self._set_view()
        self._set_shader_programs()

        # ---------- Faces program rendering
        try:
            self._scene_light.render(self._shaders)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'scene light error')

        try:
            objs = _culling.cull(
                self._object_data, self.camera.frustum_normals,
                self.camera.frustum_distances, self.camera.position.as_numpy)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'culling error')
            return

        # This 3-call order is load-bearing -- do not reorder it and do
        # not move _render_selected_overlay() earlier. The AABB/OBB/
        # floor-projection debug overlay depends on the floor already
        # being drawn (color AND depth) by the time it runs, and the
        # floor depends on real object geometry already being drawn by
        # the time IT runs (reflections need the floor's own translucent
        # surface to composite over each object's mirrored geometry-
        # shader duplicate -- see _render_selected_overlay's own
        # docstring for the full chain of reasoning). Moving the overlay
        # before the floor brings back the exact bug this ordering fixed:
        # the floor can no longer be seen through the AABB/OBB boxes
        # (either the box's depth write blocks the floor from drawing
        # under it at all, or without a depth write the floor draws over
        # and erases the box -- neither gives real translucency, because
        # alpha blending can only show B through A if B was already in
        # the color buffer when A drew).
        self._render_floor_before()
        self._draw_scene(objs)
        self._render_floor_after()
        self._render_selected_overlay()

    @_check_types.do
    def _render_selected_overlay(self):
        """Draw the selected object's AABB/OBB/floor-projection debug
        overlay -- deliberately the very last thing drawn each frame,
        after the floor (unlike everything else, which draws before it;
        see ``canvas_3d/canvas.py``'s own ``_render_floor_after`` for why
        the 3D floor specifically has to stay last relative to real
        object geometry: its own translucent surface needs to composite
        OVER each reflective object's mirrored geometry-shader duplicate
        to read as a believable tinted reflection, which only works if
        the floor draws after that geometry).

        The debug overlay has no such constraint -- it never emits a
        reflected duplicate of itself -- so there's nothing forcing it to
        draw before the floor the way real geometry is forced to. Drawing
        it after instead means its own translucent fill is blending on
        top of a framebuffer that already has the floor's (and every
        other object's) real color in it, which is what actually lets the
        floor and any other geometry show through the box rather than the
        box either erasing the floor or the floor erasing the box --
        neither of which alpha blending can produce correctly no matter
        how depth writes for the box are juggled if the floor hasn't been
        drawn yet when the box blends.

        No special depth-mask handling is needed here either: with
        nothing left to draw afterward in the frame, the overlay doesn't
        need to write its own depth for anything downstream to respect
        (see ``Base3D._render_overlay_group``'s own docstring for why it
        still disables depth writes -- that's purely so the AABB and OBB
        boxes, drawn in the same pass, don't occlude each other, not
        anything to do with the floor).
        """
        if self._selected is None:
            return

        view_obj = self._get_view_object(self._selected)

        try:
            view_obj.render_selected_overlay(self._shaders)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'selected object overlay render error')

    # ------------------------------------------------------------------
    # Snapshot (returns QImage instead of wx.Bitmap)
    # ------------------------------------------------------------------

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
