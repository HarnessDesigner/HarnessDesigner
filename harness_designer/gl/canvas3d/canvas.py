# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Self

import numpy as np
from OpenGL import GL
from OpenGL import GLU
import math
import ctypes
import weakref

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtOpenGLWidgets
from PySide6.QtCore import Signal
from PySide6.QtGui import QOpenGLContext

from . import headlight as _headlight
from . import focal_target as _focal_target
from .. import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from . import floor as _floor
from . import culling as _culling
from .. import events as _events
from ... import logger as _logger


MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS

_debug_config = _config.Config.debug.rendering3d


class CanvasEventFilter(QtCore.QObject):

    def __init__(self, canvas):
        self.canvas = canvas  # Qt: install event filter instead of canvas.Bind()

        super().__init__()
        canvas.installEventFilter(self)

    def eventFilter(self, obj, event):
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
            self.canvas._mouse_handler.handle_event(event)

        elif t in (
            QtCore.QEvent.Type.KeyPress,
            QtCore.QEvent.Type.KeyRelease
        ):
            self.canvas._key_handler.handle_event(event)

        # Mouse capture lost: Qt sends QEvent.Type.MouseButtonRelease with no
        # button held when the grab is broken externally.  For explicit
        # capture-lost notification we use QWidget.mouseGrabber() == None
        # after a grab was active.  The canvas calls this directly when
        # needed — see Canvas.changeEvent override (not required here).
        return super().eventFilter(obj, event)


class Canvas(QtOpenGLWidgets.QOpenGLWidget):
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

    def __init__(self, parent, config: "_config.Config.editor3d",
                 size: QtCore.QSize = None, axis_overlay: bool = False):

        QtOpenGLWidgets.QOpenGLWidget.__init__(self, parent)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Ensure depth buffering and double-buffering are active.
        # The model_preview canvas sets this explicitly; the main 3D canvas must too.
        # from PySide6.QtGui import QSurfaceFormat
        # fmt = QSurfaceFormat()
        # fmt.setDepthBufferSize(24)
        # fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        # self.setFormat(fmt)

        # Walk up to the QMainWindow (replaces aui.AuiManager.GetManager().GetManagedWindow())
        w = parent
        mainframe = None

        while w is not None and not hasattr(w, 'editor3d'):
            w = w.parent()
            if w is not None:
                mainframe = w

        self.mainframe = mainframe

        self.config = config
        self._mode = None

        from .. import context as _context
        from . import camera as _camera
        from . import axis_overlay as _axis_overlay

        # Create the GLContext wrapper for this widget.
        # Use it ONLY outside of initializeGL / resizeGL / paintGL —
        # Qt already makes the context current before calling those.
        self.context = _context.GLContext(self)

        if axis_overlay:
            self._axis_overlay = _axis_overlay.Overlay(parent, config.axis_overlay)
        else:
            self._axis_overlay = None

        self._init = False
        self.camera = _camera.Camera(self)
        self._angle_overlay = None

        self._faces_program = None
        self._edges_program = None
        self._vertices_program = None
        self._floor_program = None

        self.floor: _floor.Floor = None
        self._view_culling = _culling.CullingThreadPool()
        self._last_culled = []
        self._object_refs = []
        self._objects_in_view = []
        self._object_addr_mapping = {}

        self._object_data = [[], [], [], [], [], [], [], [], [], []]

        self.size = None

        self._selected = None
        self._objects = []
        self._ref_count = 0

        # angle-view overlay — now stored as a QImage instead of wx.Bitmap
        self._angle_view_image: QtGui.QImage | None = None

        from . import key_handler as _key_handler
        from . import mouse_handler as _mouse_handler
        from . import scene_light as _scene_light

        self._key_handler = _key_handler.KeyHandler(self)
        self._mouse_handler = _mouse_handler.MouseHandler(self)
        self._headlight = _headlight.Headlight(self)
        self._scene_light = _scene_light.SceneLight(self)
        self._focal_target: _focal_target.FocalPoint = None

        self._event_filter = CanvasEventFilter(self)

        if size is not None:
            self.resize(size)

        font = self.font()
        font.setPointSize(15)
        self.setFont(font)

    # ------------------------------------------------------------------
    # Properties / mode
    # -----------------------------------------------------------------

    @property
    def axis_overlay(self):
        return self._axis_overlay

    @property
    def objects_in_view(self) -> list:
        return self._objects_in_view

    def set_mode(self, mode: int) -> None:
        self._mode = mode

    # ------------------------------------------------------------------
    # Angle-view overlay
    # wx: wx.Bitmap built via wx.MemoryDC + wx.GCDC
    # Qt: QImage built via QPainter
    # ------------------------------------------------------------------

    @_debug.logfunc
    def set_angle_view(self, x, y, z):
        if None in (x, y, z):
            self._angle_view_image = None
            return

        text = f'X: {round(x, 6)}  Y: {round(y, 6)}  Z: {round(z, 6)}'

        fm = self.fontMetrics()
        w = fm.horizontalAdvance(text) + 14
        h = fm.height() + 4

        img = QtGui.QImage(w, h, QtGui.QImage.Format.Format_RGBA8888)
        img.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(img)
        painter.setFont(self.font())
        painter.setPen(QtGui.QColor(255, 255, 255, 255))
        painter.drawText(2, fm.ascent() + 2, text)
        painter.end()

        self._angle_view_image = img

    # ------------------------------------------------------------------
    # Object management (unchanged from wx version)
    # ------------------------------------------------------------------

    def set_selected(self, obj):
        self._selected = obj

    def get_selected(self):
        return self._selected

    def add_object(self, obj):
        if isinstance(obj, _focal_target.FocalPoint):
            return

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

    def __remove_obj_ref(self, ref):
        try:
            self._object_refs.remove(ref)
        except ValueError:
            pass

    def remove_object(self, obj):
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
                for line in container:
                    if line[-1] == obj_address:
                        container.remove(line)
                        break
                else:
                    continue
                break

        self.update()  # Qt: schedules a repaint (≈ wx Refresh)

    # ------------------------------------------------------------------
    # Reference-counting context manager (unchanged)
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        """wx-compatible name; delegates to Qt update()."""
        if self._ref_count:
            return

        self.update()

    # ------------------------------------------------------------------
    # Camera movement API (unchanged — called by mouse/key handlers)
    # ------------------------------------------------------------------

    @_debug.logfunc
    def TruckPedestal(self, dx: float, dy: float) -> None:
        if self.config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx
        if self.config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy
        sens = self.config.truck_pedestal.sensitivity
        self.camera.TruckPedestal(dx * sens, dy * sens, self.config.truck_pedestal.speed)

    @_debug.logfunc
    def Zoom(self, dx: float, _=None):
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    def Rotate(self, dx: float, dy: float) -> None:
        if self.config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx
        if self.config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy
        sens = self.config.rotate.sensitivity
        self.camera.Rotate(dx * sens, dy * sens)

    @_debug.logfunc
    def Walk(self, dx: float, dy: float) -> None:
        if dy == 0.0:
            self.PanTilt(dx * 6.0, 0.0)
            return
        look_dx = dx
        if self.config.walk.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx
        if self.config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy
        sens = self.config.walk.sensitivity
        self.camera.Walk(dx * sens, dy * sens, self.config.walk.speed)
        self.PanTilt(look_dx * 2.0, 0.0)

    @_debug.logfunc
    def PanTilt(self, dx: float, dy: float) -> None:
        if self.config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx
        if self.config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy
        sens = self.config.pan_tilt.sensitivity
        self.camera.PanTilt(dx * sens, dy * sens)

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle overrides
    # wx: __init__ + EVT_PAINT + EVT_SIZE + EVT_ERASE_BACKGROUND
    # Qt: initializeGL + paintGL + resizeGL  (SwapBuffers implicit)
    # ------------------------------------------------------------------

    def initializeGL(self):
        """Called once by Qt after the GL context is created.
        Qt guarantees the context is already current here — no makeCurrent needed."""

        try:
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glClearColor(*self.config.background_color)

            self._faces_program = _shaders.compile_faces_program()
            self._edges_program = _shaders.compile_edges_program()
            self._vertices_program = _shaders.compile_vertices_program()
            self._floor_program = _shaders.compile_floor_program()

            self.floor = _floor.Floor(self, self._floor_program)

            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glEnable(GL.GL_BLEND)

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
                _logger.logger.warning(f"  ! WARNING: Invalid viewport dimensions ({vw}x{vh}), using fallback 1920x1080")
                vw = 1920
                vh = 1080
            
            GL.glViewport(0, 0, vw, vh)
            self.size = (vw, vh)
            aspect = vw / float(vh) if vh else 1.0

            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(65, aspect, 0.1, 1000.0)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()

            self.camera.Set()

            self._init = True  # viewport is live; notify_virtual_size_changed may update it

            self.set_draw_grid(self.config.floor.enable)
            self.set_focal_target(self.config.focal_target.enable)

        except Exception as err:  # NOQA
            _logger.logger.traceback(err, 'initializeGL')
            raise

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
        self._virtual_w = w
        self._virtual_h = h
        self.size = (w, h)

        with self.context:
            GL.glViewport(0, 0, w, h)

        self.update()

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
            self._virtual_w = int(width * dpr)
            self._virtual_h = int(height * dpr)
            self.size = (self._virtual_w, self._virtual_h)
        # else: ignore — virtual size is managed by notify_virtual_size_changed

    def paintGL(self):
        """
        Called by Qt to render a frame. Context is already current here.
        """
        self._on_draw()

        # Angle-view overlay — rendered via OpenGL pixel blit (same algorithm).
        # Context is already current inside paintGL — no with self.context needed.
        if self._angle_view_image is not None:
            img = self._angle_view_image
            w, h = img.width(), img.height()

            pw, ph = self.parentWidget().width(), self.parentWidget().height()
            sw, sh = self.width(), self.height()

            x = (sw - pw) // 2 + 30
            y = (sh - ph) // 2 + 20
            gl_y = sh - y

            GL.glReadBuffer(GL.GL_FRONT)
            pixel_data = GL.glReadPixels(x, gl_y, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)

            # Invert colours to contrast with background (same logic as wx version)
            from PIL import Image as _PIL
            pil = _PIL.frombytes('RGBA', (w, h), bytes(pixel_data))
            # QImage → PIL for the overlay text
            img_bytes = img.bits().tobytes() if hasattr(img.bits(), 'tobytes') else bytes(img.bits())
            overlay = _PIL.frombytes('RGBA', (w, h), img_bytes)

            for y_ in range(h):
                corrected_y = h - 1 - y_
                row = corrected_y * w
                for x_ in range(w):
                    r, g, b, a = overlay.getpixel((x_, y_))
                    if a == 0:
                        continue

                    i = (row + x_) * 4
                    nr = 255 - pixel_data[i]
                    ng = 255 - pixel_data[i + 1]
                    nb = 255 - pixel_data[i + 2]
                    overlay.putpixel((x_, y_), (nr, ng, nb, a))

            # Upload the composited overlay as an OpenGL texture quad
            # (simpler than the wx GCDC path; functionally equivalent)
            rgba = overlay.tobytes('raw', 'RGBA', 0, -1)
            GL.glWindowPos2i(x + 5, sh - (y - 35) - h)
            GL.glDrawPixels(w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, rgba)

        # Qt handles buffer swap automatically — no SwapBuffers() call needed.

    # ------------------------------------------------------------------
    # Internal GL helpers (unchanged rendering logic)
    # ------------------------------------------------------------------

    def set_focal_target(self, flag):
        if flag and self._focal_target is None:
            self._focal_target = _focal_target.FocalPoint(self)
        elif not flag and self._focal_target is not None:
            self._focal_target = None

    def set_draw_grid(self, flag):
        self.floor.set(flag)

    @_debug.logfunc
    def _draw_scene(self, obj_data):
        projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        view_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

        # ---------- Faces program
        GL.glUseProgram(self._faces_program)

        # ---------- Faces program variable locations
        view_position = GL.glGetUniformLocation(
            self._faces_program, 'viewPosition')

        projection = GL.glGetUniformLocation(
            self._faces_program, 'projection')

        view = GL.glGetUniformLocation(
            self._faces_program, 'view')

        floor_y = GL.glGetUniformLocation(
            self._faces_program, 'floorY')

        object_has_reflection = GL.glGetUniformLocation(
            self._faces_program, 'objectHasReflection')

        # ---------- Faces program set variables
        GL.glUniform3fv(
            view_position, 1, self.camera.position.as_numpy)

        GL.glUniformMatrix4fv(
            projection, 1, GL.GL_FALSE, projection_matrix)

        GL.glUniformMatrix4fv(
            view, 1, GL.GL_FALSE, view_matrix)

        GL.glUniform1f(
            floor_y, self.config.floor.ground_height)

        GL.glUniform1i(
            object_has_reflection,
            int(self.config.floor.reflections.enable and
                self.config.floor.enable_floor_lock))

        # ---------- Edges program
        GL.glUseProgram(self._edges_program)

        # ---------- Edges program variable locations
        projection = GL.glGetUniformLocation(
            self._edges_program, 'projection')

        view = GL.glGetUniformLocation(
            self._edges_program, 'view')

        # ---------- Edges program set variables
        GL.glUniformMatrix4fv(
            projection, 1, GL.GL_FALSE, projection_matrix)

        GL.glUniformMatrix4fv(view, 1, GL.GL_FALSE, view_matrix)

        # ---------- Vertices program
        GL.glUseProgram(self._vertices_program)

        # ---------- Vertices program variable locations
        projection = GL.glGetUniformLocation(
            self._vertices_program, 'projection')

        view = GL.glGetUniformLocation(
            self._vertices_program, 'view')

        # ---------- Vertices program set variables
        GL.glUniformMatrix4fv(
            projection, 1, GL.GL_FALSE, projection_matrix)

        GL.glUniformMatrix4fv(
            view, 1, GL.GL_FALSE, view_matrix)

        # ---------- Faces program rendering
        GL.glUseProgram(self._faces_program)

        # ---------- Faces program set lighting
        self._scene_light.set(self._faces_program)
        self._headlight(self._faces_program)

        removed_objects = []
        objects_in_view = []

        for row in obj_data:
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
            obj.obj3d.render(self._faces_program, self._edges_program, self._vertices_program)

        GL.glUseProgram(0)
        self._objects_in_view = objects_in_view

        for row in removed_objects:
            for container in self._object_data:
                try:
                    container.remove(row)
                    break
                except ValueError:
                    continue

    @_debug.logfunc
    def _on_draw(self):
        # Use the virtual canvas size for the aspect ratio, not the widget
        # geometry.  This prevents distortion when the surrounding panel is
        # resized (mirrors the wx SetVirtualSize behaviour).
        if self.size:
            w, h = self.size
        else:
            w = self.width()
            h = self.height()

        aspect = w / float(h) if h else 1.0

        f_size = self.config.floor.grid.size ** 2

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        GL.glLineWidth(2.0)

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(65, aspect, 0.1, float(math.sqrt(f_size * f_size)))

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        self.camera.Set()

        objs = self._view_culling.cull(
            self._object_data, self.camera.frustum_normals,
            self.camera.frustum_distances, self.camera.position.as_numpy)

        self._draw_scene(objs)

        if self.config.focal_target.enable and self._focal_target is not None:
            GL.glUseProgram(self._faces_program)
            self._focal_target.obj3d.render(
                self._faces_program, self._edges_program, self._vertices_program)
            GL.glUseProgram(0)

        self.floor.render(self._floor_program)

        if self._axis_overlay is not None:
            self._axis_overlay.set_angle(
                (self.camera.position - self.camera.focal_position).inverse)

        # Qt handles SwapBuffers automatically — removed.

    # ------------------------------------------------------------------
    # Snapshot (returns QImage instead of wx.Bitmap)
    # ------------------------------------------------------------------

    def take_snapshot(self) -> QtGui.QImage:
        # take_snapshot is called outside of paintGL so we must acquire
        # the context explicitly via the context manager.
        with self.context:
            w = self.width()
            h = self.height()

            GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
            data = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)

            arr = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 3))
            arr = np.flipud(arr)

            img = QtGui.QImage(arr.tobytes(), w, h, w * 3, QtGui.QImage.Format.Format_RGB888)
            return img.copy()   # copy so the buffer outlives arr

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
