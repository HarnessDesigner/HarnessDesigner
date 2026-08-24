# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg Board Editor Canvas using OpenGL

Phase 1 skeleton: camera/pan/zoom/grid plumbing only, mirroring
gl.canvas_schematic.canvas.Canvas exactly where its pattern is canvas-agnostic
(GLContext usage, Camera-based orthographic projection, background
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

from PySide6.QtCore import QSize
from OpenGL import GL
import numpy as np

from ... import config as _config
from . import floor as _floor2d
from . import mouse_handler as _mouse_handler2d
from . import camera as _camera
from ..canvas_base import canvas_base as _canvas_base


from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


class Canvas(_canvas_base.CanvasBase):

    _floor: _floor2d.Floor = None
    camera: _camera.Camera = None
    _mouse_handler: _mouse_handler2d.MouseHandler = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 config: _config.Config.editor_pegboard = None,
                 size: QSize = None):

        super().__init__(mainframe, config, size)

        self.camera = _camera.Camera(self)
        self._mouse_handler = _mouse_handler2d.MouseHandler(self)

    @_check_types.do
    def set_draw_floor(self, value) -> None:
        """Show/hide the reference grid.

        :param value: New grid-visibility state.
        :type value: UNKNOWN
        """
        self.config.floor.enable = bool(value)
        self._floor.set(self.config.floor.enable)
        self.update()

    @_check_types.do
    def initializeGL(self):
        """One-time GL setup. Qt guarantees the context is already current here."""

        self._floor = _floor2d.Floor(self)

        super().initializeGL()

    @_check_types.do
    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize. Context is already current here."""
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)
        self.update()

    def _render_floor_before(self):
        try:
            self._floor.render(self._shaders)
        except:  # NOQA
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def _get_view_object(obj):
        return obj.objpegboard

    def _set_view(self):
        """Build the orthographic projection matrix for the current
        camera distance/focal_position and store it on the camera.

        Same box convention as Camera2D.objects_in_view/screen_to_world/
        world_to_screen (world_per_pixel = distance / 1000.0, centered on
        focal_position.x/.z) -- computed locally instead of applied via
        GL.glOrtho and read back from GL.

        Failsafe only -- rebuilt when the camera actually moves (marked
        dirty by Camera2D's own pan/zoom methods), not unconditionally
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
