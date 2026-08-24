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

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize
import numpy as np

from ... import config as _config
from . import camera as _camera
from . import mouse_handler as _mouse_handler2d
from ... import check_types as _check_types
from ..canvas_base import canvas_base as _canvas_base
from . import floor as _floor2d


if TYPE_CHECKING:
    from ... import ui as _ui


class Canvas(_canvas_base.CanvasBase):
    """
    2D OpenGL Canvas for Schematic Editor.

    Provides orthographic 2D view with:
    - 1:1 mm mapping (same as 3D canvas)
    - Pan and zoom capabilities
    - Object selection and dragging
    - Point-based coordinate system
    - Snap-to-grid functionality
    """

    _floor: _floor2d.Floor = None
    camera: _camera.Camera = None
    _mouse_handler: _mouse_handler2d.MouseHandler = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 config: _config.Config.editor_schematic,
                 size: QSize = None):
        """Initialise the :class:`Canvas` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor_schematic`
        :param size: Value for ``size``.
        :type size: :class:`QSize`
        """
        super().__init__(mainframe, config, size)

        self.camera = _camera.Camera(self)
        self._mouse_handler = _mouse_handler2d.MouseHandler(self)

    # ------------------------------------------------------------------
    # Object management
    # ------------------------------------------------------------------

    @_check_types.do
    def initializeGL(self):
        """One-time GL setup (replaces _init_gl called from _on_paint).
        Qt guarantees the context is already current here.
        """

        self._floor = _floor2d.Floor(self)

        super().initializeGL()

    @staticmethod
    def _get_view_object(obj):
        return obj.objschematic

    def _render_floor_before(self):
        try:
            self._floor.render(self._shaders)
        except:  # NOQA
            import traceback
            traceback.print_exc()
            raise

    @_check_types.do
    def _set_view(self):
        """Build the orthographic projection matrix for the current
        camera distance/focal_position and store it on the camera.

        Same box convention as Camera.objects_in_view/screen_to_world/
        world_to_screen (world_per_pixel = distance / 1000.0, centered on
        focal_position.x/.z) -- computed locally instead of applied via
        GL.glOrtho and read back from GL.

        Failsafe only -- rebuilt when the camera actually moves (marked
        dirty by Camera's own pan/zoom methods), not unconditionally
        every frame. The render surface is a fixed virtual size that a
        plain window resize never changes, so there's no other source of
        staleness to guard against here.
        """
        if not self.camera.is_dirty:
            return

        if self.size is None:
            return

        width, height = self.size
        if width == 0 or height == 0:
            return

        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        focal_x, _, focal_z = self.camera.focal_position.as_float

        left = focal_x - half_width
        right = focal_x + half_width
        bottom = focal_z - half_height
        top = focal_z + half_height
        near, far = -1.0, 1.0

        projection = np.zeros((4, 4), dtype=np.float32)
        projection[0, 0] = 2.0 / (right - left)
        projection[1, 1] = 2.0 / (top - bottom)
        projection[2, 2] = -2.0 / (far - near)
        projection[0, 3] = -(right + left) / (right - left)
        projection[1, 3] = -(top + bottom) / (top - bottom)
        projection[2, 3] = -(far + near) / (far - near)
        projection[3, 3] = 1.0

        modelview = np.identity(4, dtype=np.float32)

        self.camera.set_view(projection, modelview)
