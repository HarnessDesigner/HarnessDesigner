# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Procedural top-down dot-grid floor for the schematic editor.

Renders entirely inside one fragment shader on a single quad, resized
every frame to exactly cover the current viewport. The dot grid is a
single power-of-2 tier (see :meth:`Floor._current_spacing`) rather than
a major/minor "nice value" (1, 5, 10, 50, ...) pair -- dropped after
visual testing showed the nice-value sequence's uneven jump ratios (5x
then 2x) read as an inconsistent, sometimes near-empty-looking grid, and
the two tiers weren't visually distinguishable enough to tell apart
anyway.
"""

from typing import TYPE_CHECKING

from OpenGL import GL
import numpy as np
import ctypes
import math

from ...geometry.decimal import Decimal as _d
from ..canvas_base import floor_base as _floor_base


if TYPE_CHECKING:
    from . import canvas as _canvas
    from .. import shaders as _shaders


# ═══════════════════════════════════════════════════════════════════════════════
#  Geometry
# ═══════════════════════════════════════════════════════════════════════════════
def _build_quad(left: float | _d, right: float | _d, bottom: float, top: float | _d) -> np.ndarray:
    """
    Two triangles covering the given world-space rectangle, flat vec2 array.
    """

    return np.array([
        float(left), float(bottom), float(right),
        float(bottom), float(right), float(top),
        float(left), float(bottom), float(right),
        float(top), float(left), float(top)], dtype=np.float32)

# ═══════════════════════════════════════════════════════════════════════════════
#  Floor class
# ═══════════════════════════════════════════════════════════════════════════════


class Floor(_floor_base.FloorBase):
    """Procedural top-down dot grid."""

    def __init__(self, canvas: '_canvas.Canvas'):
        super().__init__(canvas)

        self.grid_spacing = 1.0

    def _initialize_grid(self):
        # placeholder bounds, updated every render()
        verts = _build_quad(-1.0, 1.0, -1.0, 1.0)

        vao = GL.glGenVertexArrays(1)
        vbo = GL.glGenBuffers(1)

        GL.glBindVertexArray(vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, verts.nbytes, verts, GL.GL_DYNAMIC_DRAW)

        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 2 * 4, ctypes.c_void_p(0))

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

        return vao, vbo

    def set(self, flag):
        """
        Enable or disable the floor, rebuilding GPU resources as needed.
        """

        with self.canvas.context:
            if self._vao is not None:
                try:
                    GL.glDeleteVertexArrays(1, [self._vao])
                except Exception:  # NOQA
                    pass
                try:
                    GL.glDeleteBuffers(1, [self._vbo])
                except Exception:  # NOQA
                    pass

                self._vao = None
                self._vbo = None

            if flag:
                self._vao, self._vbo = self._initialize_grid()

        self.canvas.Refresh(False)

    def _current_spacing(self, world_per_pixel: float) -> float:
        """Return the current world-space dot spacing: ``2**n`` for
        whatever integer *n* (positive, negative, or zero) keeps this
        tier's own on-screen spacing within ``[target/2, target]`` (see
        Config.floor.target_dot_pixel_spacing's own docstring for the
        exact rule and why) -- unbounded in both directions, so zooming
        in past 1.0 keeps subdividing (0.5, 0.25, ...) exactly the same
        way zooming out keeps doubling.

        ``raw`` is the spacing that would put dots *exactly* at the
        target pixel spacing at the current zoom; flooring
        ``log2(raw)`` picks the largest power-of-2 tier at or below
        that, which is what keeps the *current* tier's on-screen size
        inside that half-to-full-target window instead of jumping past
        it in either direction.
        """
        target_px = float(self.config.target_dot_pixel_spacing)
        raw = target_px * world_per_pixel

        if raw <= 0.0:
            return 1.0

        n = math.floor(math.log2(raw))
        return float(2.0 ** n)

    def render(self, shaders: "_shaders.ShaderProgram"):
        """Draw the procedural floor in a single pass."""

        if not self.config.enable or self._vao is None:
            return

        program = shaders.grid

        size = self.canvas.size
        if size is None:
            return

        width, height = size
        if width == 0 or height == 0:
            return

        camera = self.canvas.camera

        # Same box the camera's own _set_view() just built (world_per_pixel
        # = distance / 1000.0, centered on focal_position.x/.z) -- read the
        # matrix it already computed rather than independently recomputing
        # a second, possibly-diverging copy of the same box.
        world_per_pixel = camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        focal_x, _, focal_z = camera.focal_position.as_float

        left = focal_x - half_width
        right = focal_x + half_width
        bottom = focal_z - half_height
        top = focal_z + half_height

        self.grid_spacing = self._current_spacing(world_per_pixel)

        with self.canvas.context, program:
            verts = _build_quad(left, right, bottom, top)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, verts.nbytes, verts)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            program.projection = camera.projection.T
            program.spacing = self.grid_spacing
            program.world_per_pixel = world_per_pixel
            program.dot_color = self.config.dot_color

            GL.glBindVertexArray(self._vao)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)
            GL.glBindVertexArray(0)
