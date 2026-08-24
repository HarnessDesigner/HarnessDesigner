# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from OpenGL import GL
import math
import numpy as np
from PySide6 import QtCore

from . import focal_target as _focal_target
from ... import debug as _debug
from ... import config as _config
from . import floor as _floor3d
from . import camera as _camera
from . import headlight as _headlight
from ... import logger as _logger
from ... import check_types as _check_types
from . import mouse_handler as _mouse_handler3d
from ..canvas_base import canvas_base as _canvas_base


if TYPE_CHECKING:
    from ... import ui as _ui

_debug_config = _config.Config.debug.rendering3d


def _build_perspective_matrix(fov_deg: float, aspect: float,
                              near: float, far: float) -> np.ndarray:
    """
    Row-major (``matrix @ column_vector``) perspective projection matrix,
    equivalent to what ``gluPerspective`` would produce -- built locally
    here instead of applied via GLU and read back from GL.

    This is what replaced the old ``GLU.gluPerspective(65, aspect, 0.1,
    1000.0)`` call that used to run once in ``initializeGL()`` -- that
    call wrote into the legacy fixed-function ``GL_PROJECTION_MATRIX``
    register, which nothing reads anymore (no immediate-mode rendering
    exists in this codebase, and ``_set_shader_programs()`` uploads
    ``camera.projection`` -- the numpy array this function returns,
    stored via ``camera.set_view()`` -- directly as a shader uniform
    instead of reading that register back). Unlike the old call, this
    one runs every frame from ``_set_view()`` with the *current* aspect
    ratio, not a stale one frozen at construction time.
    """

    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)

    matrix = np.zeros((4, 4), dtype=np.float32)
    matrix[0, 0] = f / aspect
    matrix[1, 1] = f
    matrix[2, 2] = (far + near) / (near - far)
    matrix[2, 3] = (2.0 * far * near) / (near - far)
    matrix[3, 2] = -1.0

    return matrix


def _build_lookat_matrix(position: np.ndarray, forward: np.ndarray,
                         up: np.ndarray) -> np.ndarray:
    """
    Row-major (``matrix @ column_vector``) view matrix for a camera at
    *position* looking along *forward*, equivalent to what ``gluLookAt``
    would produce -- built locally here instead of applied via GLU and
    read back from GL. *up* is expected already orthogonal to *forward*
    (as produced by ``Camera._calculate_camera()``).
    """

    side = np.cross(forward, up)  # NOQA

    matrix = np.identity(4, dtype=np.float32)
    matrix[0, 0:3] = side
    matrix[1, 0:3] = up
    matrix[2, 0:3] = -forward
    matrix[0, 3] = -np.dot(side, position)
    matrix[1, 3] = -np.dot(up, position)
    matrix[2, 3] = np.dot(forward, position)

    return matrix


class Canvas(_canvas_base.CanvasBase):
    """
    3D perspective GL canvas -- the free-orbit camera view (housing/wire
    editor). See CanvasBase for the shared wx->Qt QOpenGLWidget lifecycle
    notes (paintGL/resizeGL/initializeGL, signals replacing wx events).

    Owns the perspective Camera, the floor grid, the headlight, and the
    focal-target indicator; _set_view() builds the perspective/look-at
    matrices this view specifically needs.
    """

    camera: _camera.Camera = None
    _floor: _floor3d.Floor = None
    _mouse_handler: _mouse_handler3d.MouseHandler = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 config: _config.Config.editor_3d,
                 size: QtCore.QSize = None):
        """Initialise the :class:`Canvas` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor_3d`
        :param size: Value for ``size``.
        :type size: :class:`QtCore.QSize`
        """

        super().__init__(mainframe, config, size)

        self.camera = _camera.Camera(self)
        self._mouse_handler = _mouse_handler3d.MouseHandler(self)

        self._headlight: _headlight.Headlight = None
        self._focal_target: _focal_target.FocalPoint = None

    # ------------------------------------------------------------------
    # Properties / mode
    # -----------------------------------------------------------------

    @property
    @_check_types.do
    def axis_overlay(self):
        """Return the axis overlay.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.parent()._axis_overlay  # NOQA

    @_check_types.do
    def initializeGL(self):
        """Called once by Qt after the GL context is created.
        Qt guarantees the context is already current here — no makeCurrent needed."""

        try:
            self._floor = _floor3d.Floor(self)
            super().initializeGL()

            self._headlight = _headlight.Headlight(self)

            self._focal_target = _focal_target.FocalPoint(self)
            self.set_focal_target(self.config.focal_target.enable)

            self.update()
            self.repaint()

        except Exception as err:  # NOQA
            _logger.traceback(err, 'initializeGL')
            raise

    @_check_types.do
    def set_focal_target(self, flag: bool):
        """Show/hide the focal-target indicator -- called from the
        focal-target toggle button, and once at startup from
        initializeGL() with the persisted config value.

        Sets Base3D.is_visible on the underlying 3D object; render()
        already checks that internally (`if not self.is_visible: return`),
        so nothing else needs to gate on it separately.

        :param flag: Whether the focal target should be visible.
        :type flag: bool
        """
        if self._focal_target is not None:
            self._focal_target.obj3d.is_visible = flag

    def _set_view(self):
        if self.size:
            w, h = self.size
        else:
            w = self.width()
            h = self.height()

        aspect = w / float(h) if h else 1.0

        f_size = self.config.floor.grid.size ** 2

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        GL.glLineWidth(2.0)

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        fov_deg = 65.0
        near = 0.1
        far = float(math.sqrt(f_size * f_size))

        projection = _build_perspective_matrix(fov_deg, aspect, near, far)
        modelview = _build_lookat_matrix(
            self.camera.position.as_numpy, self.camera.forward, self.camera.up)

        self.camera.set_view(projection, modelview, fov_deg)

    @staticmethod
    def _get_view_object(obj):
        return obj.obj3d

    def _render_floor_after(self):
        try:
            self._floor.render(self._shaders)
        except:  # NOQA
            import traceback
            traceback.print_exc()
            raise

    @_debug.logfunc
    @_check_types.do
    def _on_draw(self):
        super()._on_draw()

        try:
            self._headlight.set(self._shaders)
        except Exception as err:  # NOQA
            _logger.traceback(err, 'headlight error')

        if self._focal_target is not None:
            # No visibility check needed here -- render() already checks
            # is_visible internally (set_focal_target() is the one place
            # that toggles it) and no-ops if it's off. render() binds
            # whichever program(s) it needs itself.
            try:
                self._focal_target.obj3d.render(self._shaders)
            except Exception as err:  # NOQA
                _logger.traceback(err, 'focal target error')

        if self.axis_overlay is not None:
            self.axis_overlay.set_angle(
                (self.camera.position - self.camera.focal_position).inverse)
