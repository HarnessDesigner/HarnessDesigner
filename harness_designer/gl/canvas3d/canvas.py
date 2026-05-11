# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Self

import numpy as np
from OpenGL import GL
from OpenGL import GLU
import math
import ctypes
import weakref

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QImage
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal

from . import headlight as _headlight
from . import focal_target as _focal_target
from .. import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from . import floor as _floor
from . import culling as _culling
from .. import events as _events


MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS

_debug_config = _config.Config.debug.rendering3d


class Canvas(QOpenGLWidget):
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

    # --- GL canvas signals (replace wx.PyEventBinder / ProcessEvent) ---
    # object events
    gl_object_selected     = Signal(object)
    gl_object_unselected   = Signal(object)
    gl_object_activated    = Signal(object)
    gl_object_right_click  = Signal(object)
    gl_object_right_dclick = Signal(object)
    gl_object_middle_click  = Signal(object)
    gl_object_middle_dclick = Signal(object)
    gl_object_aux1_click   = Signal(object)
    gl_object_aux1_dclick  = Signal(object)
    gl_object_aux2_click   = Signal(object)
    gl_object_aux2_dclick  = Signal(object)
    gl_object_drag         = Signal(object)
    # key events
    gl_key_down    = Signal(object)
    gl_key_up      = Signal(object)
    # mouse events
    gl_mouse_move  = Signal(object)
    gl_left_down   = Signal(object)
    gl_left_up     = Signal(object)
    gl_left_dclick = Signal(object)
    gl_right_down   = Signal(object)
    gl_right_up     = Signal(object)
    gl_right_dclick = Signal(object)
    gl_middle_down   = Signal(object)
    gl_middle_up     = Signal(object)
    gl_middle_dclick = Signal(object)
    gl_aux1_down   = Signal(object)
    gl_aux1_up     = Signal(object)
    gl_aux1_dclick = Signal(object)
    gl_aux2_down   = Signal(object)
    gl_aux2_up     = Signal(object)
    gl_aux2_dclick = Signal(object)
    # misc
    gl_capture_lost = Signal(object)

    def __init__(self, parent, config: "_config.Config.editor3d",
                 size: QSize = None, axis_overlay: bool = False):
        super().__init__(parent)

        # Walk up to the QMainWindow (replaces aui.AuiManager.GetManager().GetManagedWindow())
        w = parent
        while w is not None and not hasattr(w, 'editor3d'):
            w = w.parent()
        self.mainframe = w if w is not None else parent

        self.config = config
        self._mode = None

        from .. import context as _context
        from . import camera as _camera
        from . import axis_overlay as _axis_overlay

        if axis_overlay:
            self._axis_overlay = _axis_overlay.Overlay(self, config.axis_overlay)
        else:
            self._axis_overlay = None

        self._init = False
        self.context = _context.GLContext(self)
        self.camera = _camera.Camera(self)
        self._angle_overlay = None

        self._faces_program   = None
        self._edges_program   = None
        self._vertices_program = None
        self._floor_program   = None

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
        self._angle_view_image: QImage | None = None

        from . import key_handler as _key_handler
        from . import mouse_handler as _mouse_handler
        from . import scene_light as _scene_light

        self._key_handler   = _key_handler.KeyHandler(self)
        self._mouse_handler = _mouse_handler.MouseHandler(self)
        self._headlight     = _headlight.Headlight(self)
        self._scene_light   = _scene_light.SceneLight(self)
        self._focal_target: _focal_target.FocalPoint = None

        if size is not None:
            self.resize(size)

        font = self.font()
        font.setPointSize(15)
        self.setFont(font)

    # ------------------------------------------------------------------
    # Properties / mode
    # ------------------------------------------------------------------

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

        from PySide6.QtGui import QPainter, QColor, QPen
        from PySide6.QtCore import QRectF

        text = f'X: {round(x, 6)}  Y: {round(y, 6)}  Z: {round(z, 6)}'

        fm = self.fontMetrics()
        w = fm.horizontalAdvance(text) + 14
        h = fm.height() + 4

        img = QImage(w, h, QImage.Format_RGBA8888)
        img.fill(Qt.transparent)

        painter = QPainter(img)
        painter.setFont(self.font())
        painter.setPen(QColor(255, 255, 255, 255))
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
        """Called once by Qt after the GL context is created."""
        self._init_gl()
        self._init = True

    def resizeGL(self, width: int, height: int):
        """
        Called by Qt whenever the widget is resized.
        wx: EVT_SIZE → wx.CallAfter(_do_set_viewport, event.GetSize())
        Qt: resizeGL is already called on the main thread after resize;
            no deferred scheduling needed.
        """
        dpr = self.devicePixelRatio()
        w = int(width * dpr)
        h = int(height * dpr)
        self.size = (w, h)
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        """
        Called by Qt to render a frame.
        wx: EVT_PAINT → _on_paint → wx.PaintDC(self) + context.acquire() + _on_draw()
        Qt: paintGL already runs with the context current; no PaintDC needed.
        """
        if not self._init:
            # Shouldn't happen (initializeGL runs first), but guard anyway.
            self._init_gl()
            self._init = True

        self._on_draw()

        # Angle-view overlay — rendered via OpenGL pixel blit (same algorithm).
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

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v if n == 0.0 else v / n

    @_debug.logfunc
    def _init_gl(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(*self.config.background_color)

        self._faces_program    = _shaders.compile_faces_program()
        self._edges_program    = _shaders.compile_edges_program()
        self._vertices_program = _shaders.compile_vertices_program()
        self._floor_program    = _shaders.compile_floor_program()

        self.floor = _floor.Floor(self, self._floor_program)

        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

        self.camera.Set()

        w, h = self.width(), self.height()
        aspect = w / float(h) if h else 1.0

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(65, aspect, 0.1, 1000.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        self.set_draw_grid(self.config.floor.enable)
        self.set_focal_target(self.config.focal_target.enable)

        # wx.CallAfter → QTimer.singleShot(0, …)
        QTimer.singleShot(0, lambda: self.Zoom(1.0))

    def set_focal_target(self, flag):
        with self.context:
            if flag and self._focal_target is None:
                self._focal_target = _focal_target.FocalPoint(self)
            elif not flag and self._focal_target is not None:
                self._focal_target = None

    def set_draw_grid(self, flag):
        self.floor.set(flag)

    @_debug.logfunc
    def _draw_scene(self, obj_data):
        projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        view_matrix       = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

        GL.glUseProgram(self._faces_program)
        GL.glUniform3fv(GL.glGetUniformLocation(self._faces_program, "viewPosition"),
                        1, self.camera.position.as_numpy)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._faces_program, "projection"),
                              1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._faces_program, "view"),
                              1, GL.GL_FALSE, view_matrix)
        GL.glUniform1f(GL.glGetUniformLocation(self._faces_program, "floorY"),
                       self.config.floor.ground_height)
        GL.glUniform1i(GL.glGetUniformLocation(self._faces_program, "objectHasReflection"),
                       int(self.config.floor.reflections.enable and self.config.floor.enable_floor_lock))

        GL.glUseProgram(self._edges_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._edges_program, "projection"),
                              1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._edges_program, "view"),
                              1, GL.GL_FALSE, view_matrix)

        GL.glUseProgram(self._vertices_program)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._vertices_program, "projection"),
                              1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(self._vertices_program, "view"),
                              1, GL.GL_FALSE, view_matrix)

        GL.glUseProgram(self._faces_program)
        self._scene_light.set(self._faces_program)
        self._headlight(self._faces_program)

        removed_objects  = []
        objects_in_view  = []

        for row in obj_data:
            ref_address = row[-1]
            obj_ref = ctypes.cast(ref_address, ctypes.py_object).value
            obj     = obj_ref()

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
        self.context.acquire()
        w   = self.width()
        h   = self.height()
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

        if self._axis_overlay is not None:
            self.context.release()
            self._axis_overlay.set_angle(
                (self.camera.position - self.camera.focal_position).inverse)
            self.context.acquire()

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

        # Qt handles SwapBuffers automatically — removed.

        self.context.release()

    # ------------------------------------------------------------------
    # Snapshot (returns QImage instead of wx.Bitmap)
    # ------------------------------------------------------------------

    def take_snapshot(self) -> QImage:
        self.makeCurrent()
        w = self.width()
        h = self.height()

        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        data = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)

        arr = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 3))
        arr = np.flipud(arr)

        img = QImage(arr.tobytes(), w, h, w * 3, QImage.Format_RGB888)
        return img.copy()   # copy so the buffer outlives arr
