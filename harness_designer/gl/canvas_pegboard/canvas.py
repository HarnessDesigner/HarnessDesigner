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
    _editor_name = 'editor_pegboard'

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

        GL.glDepthFunc(GL.GL_LESS)

    @_check_types.do
    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize. Context is already current here."""
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)
        self.update()

    def _render_floor_after(self):
        try:
            self._floor.render(self._shaders)
        except:  # NOQA
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def _get_view_object(obj):
        return obj.objpegboard

    @property
    @_check_types.do
    def light_position(self) -> np.ndarray:
        """Fixed light, angled off-vertical -- see ``CanvasBase.
        light_position``'s own docstring for why the base's camera-eye
        default (coincident with a permanently straight-down camera)
        gives flat, shadeless lighting here. Offset from the current
        focal point (not the camera eye) so panning doesn't leave it
        behind, and independent of zoom (``camera.distance``) so it
        doesn't dim/brighten as the user zooms.
        """
        focal = self.camera.focal_position.as_numpy
        return focal + np.array([300.0, 500.0, -300.0], dtype=np.float32)

    @property
    @_check_types.do
    def view_position(self) -> np.ndarray:
        """Fixed height directly above the current focal point, NOT
        ``camera.position`` -- see ``CanvasBase.view_position``'s own
        docstring for why the base's camera-eye default is wrong here:
        this camera's ``position.y`` IS its zoom distance (``Camera.
        distance``), so it can sit as little as 10 world units above the
        board when zoomed in, close enough that ``viewDir`` (faces.py's
        fragment shader) swings sharply across even a modest-length
        surface instead of the near-constant direction a genuine
        orthographic eye-at-infinity gives -- confirmed 2026-09-13 as
        the cause of a wire's cylinder appearing to taper to a point at
        each end when zoomed in. Reuses the exact same fixed offset
        ``light_position`` already uses above, for the same
        zoom-independence reason (that offset was already correct for a
        genuinely-far, angled light; equally fine reused as a stand-in
        "eye" here since a top-down view's specular highlight is a
        rough shape cue, not a precise reflection this needs to get
        exactly right).
        """
        focal = self.camera.focal_position.as_numpy
        return focal + np.array([300.0, 500.0, -300.0], dtype=np.float32)

    def _on_draw(self):
        self.mainframe.bounds_manager.editor_pegboard.obb.reset_visible()
        self.mainframe.bounds_manager.editor_pegboard.aabb.reset_visible()

        super()._on_draw()

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

        # modelview is identity (see below) -- world Y feeds directly into
        # this near/far range with no camera-relative transform in between,
        # so it's really just "how much of the world's Y axis is visible."
        # `near` needs to clear the floor, drawn at y=-100.0 (see
        # gl.shaders.grid2d's own vertex shader); `far` needs real headroom
        # above it for real part geometry, inherited from canvas_schematic's
        # own Phase 1 skeleton as a +1.0 placeholder that's invisible there
        # (schematic draws small symbolic flat primitives) but clips away
        # virtually all real geometry here, since the peg board reuses
        # actual physical-scale 3D part meshes (tens to hundreds of mm
        # tall) sitting above the floor -- widened to this file's own
        # 1000-unit world-scale convention (see world_per_pixel above) so
        # real part geometry is never clipped regardless of how tall it is.
        near, far = -101.0, 1000.0

        # modelview is identity, so this projection alone has to pick which
        # world axis is "depth" -- gl_Position = projection * vec4(world, 1)
        # in faces.py's vertex shader means matrix ROW 1 reads the vertex's
        # Y component and ROW 2 reads its Z component, regardless of which
        # world axis the bounds used to build that row came from. Row 1
        # (screen-vertical) reads column 2 (world Z), row 2 (depth) reads
        # column 1 (world Y).
        #
        # Row 1 only is negated (both the scale AND the paired translation
        # term, to keep a valid [-1,1] range) -- this camera is permanently
        # locked looking straight down -Y. Verified against the actual
        # render-matrix vectors the free 3D camera uses (`side = cross(
        # forward, up)`/`up = cross(forward, right)` from gl.canvas_3d.
        # camera.build_lookat_matrix/CameraBase._calculate_camera -- NOT
        # camera.right directly, which is the negative of `side` and is a
        # separate, distinct inconsistency in this codebase), taken to
        # their continuous limit as forward approaches straight down (-Y)
        # from the same +Z side the app's default camera sits on: side
        # stays (1,0,0) (row 0 was already correct, confirmed 2026-09-11
        # against a real dragged-object test in the 3D editor), up becomes
        # (0,0,-1) for a camera ABOVE looking down. The un-negated row 1
        # below matched up=(0,0,1) instead -- exactly what the same limit
        # gives for a camera BELOW the board looking up, which is why
        # housings rendered showing their underside instead of their top.
        projection = np.zeros((4, 4), dtype=np.float32)
        projection[0, 0] = 2.0 / (right - left)
        projection[1, 2] = -2.0 / (top - bottom)
        projection[2, 1] = -2.0 / (far - near)
        projection[0, 3] = -(right + left) / (right - left)
        projection[1, 3] = (top + bottom) / (top - bottom)
        projection[2, 3] = -(far + near) / (far - near)
        projection[3, 3] = 1.0

        modelview = np.identity(4, dtype=np.float32)

        self.camera.set_view(projection, modelview)
