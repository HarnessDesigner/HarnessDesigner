# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from OpenGL import GL
import numpy as np
import ctypes
from ... import check_types as _check_types
from .. canvas_base import floor_base as _floor_base

if TYPE_CHECKING:
    from . import canvas as _canvas
    from .. import shaders as _shaders


# ═══════════════════════════════════════════════════════════════════════════════
#  Geometry
# ═══════════════════════════════════════════════════════════════════════════════

@_check_types.do
def _build_floor_quad(floor_size, floor_height):
    """Return a single quad that covers the entire floor area.

    The procedural fragment shader computes every visual detail
    (tiles, major lines, minor dashed lines) from world coordinates,
    so only position is required as a vertex attribute.
    """
    h = floor_size / 2.0
    y = float(floor_height)

    verts = np.array([
        -h, y, -h,   # front-left
        h, y, -h,   # front-right
        h, y, h,   # back-right
        -h, y, h,   # back-left
    ], dtype=np.float32)

    idx = np.array([0, 1, 2,  0, 2, 3], dtype=np.uint32)

    return verts, idx


# ═══════════════════════════════════════════════════════════════════════════════
#  Floor class
# ═══════════════════════════════════════════════════════════════════════════════

class Floor(_floor_base.FloorBase):
    """Procedural floor grid.

    Renders checkerboard tiles, major solid lines, and minor dashed lines
    entirely inside one fragment shader on a single large quad.

    This approach eliminates the orientation-dependent moiré that occurs
    when thin geometry quads are rasterised at sub-pixel widths, because
    the shader computes every line analytically using screen-space
    derivatives (fwidth) rather than relying on the rasteriser to hit
    thin geometry.

    Always renders with `ShaderProgram().floor` -- fetched directly here,
    never passed in from a caller.
    """

    @_check_types.do
    def __init__(self, canvas: '_canvas.Canvas'):
        super().__init__(canvas)

        self._ebo = None
        self._n = None

    # ─────────────────────────────────────────────────────────────────────────

    @_check_types.do
    def _initialize_grid(self):
        verts, idx = _build_floor_quad(
            self.config.size, self.config.ground_height)

        vao = GL.glGenVertexArrays(1)
        vbo, ebo = GL.glGenBuffers(2)

        GL.glBindVertexArray(vao)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER, verts.nbytes, verts, GL.GL_STATIC_DRAW)

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, ebo)
        GL.glBufferData(
            GL.GL_ELEMENT_ARRAY_BUFFER, idx.nbytes, idx, GL.GL_STATIC_DRAW)

        # Position only — stride = 3 floats × 4 bytes
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(
            0, 3, GL.GL_FLOAT, GL.GL_FALSE, 3 * 4, ctypes.c_void_p(0))

        GL.glBindVertexArray(0)

        return vao, vbo, ebo, len(idx)

    # ─────────────────────────────────────────────────────────────────────────

    @_check_types.do
    def set(self, flag):
        """Enable or disable the floor, rebuilding GPU resources as needed."""

        if self._vao is not None:
            with self.canvas.context:
                try:
                    GL.glDeleteVertexArrays(1, [self._vao])
                except Exception:  # NOQA
                    pass
                try:
                    GL.glDeleteBuffers(2, [self._vbo, self._ebo])
                except Exception:  # NOQA
                    pass
                self._vao = None
                self._vbo = None
                self._ebo = None
                self._n = None

        if flag:
            with self.canvas.context:
                self._vao, self._vbo, self._ebo, self._n = self._initialize_grid()

        self.canvas.Refresh(False)

    # ─────────────────────────────────────────────────────────────────────────

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        """Draw the procedural floor in a single pass."""

        if not self.config.enable or self._vao is None:
            return

        program = shaders.floor

        with self.canvas.context, program:
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glEnable(GL.GL_MULTISAMPLE)

            # MVP ─────────────────────────────────────────────────────────────────
            program.mvp = self.canvas.camera.clip

            # Grid dimensions ─────────────────────────────────────────────────────
            cfg = self.config.grid
            has_minor = 1 if cfg.enable else 0
            tile_size = cfg.size
            minor_sz = tile_size / (cfg.secondary_lines_per_tile + 1)

            program.tile_size = tile_size
            program.minor_spacing = minor_sz
            program.has_minor_grid = has_minor

            # Tile colours ────────────────────────────────────────────────────────
            program.color_a = cfg.primary_color
            program.color_b = cfg.secondary_color

            # Line colours ────────────────────────────────────────────────────────
            program.major_color = cfg.primary_line_color
            program.minor_color = cfg.secondary_line_color

            # Line widths ─────────────────────────────────────────────────────────
            program.major_width = cfg.primary_line_width
            program.minor_width = cfg.secondary_line_width

            # Dash parameters ─────────────────────────────────────────────────────
            program.stipple_pattern = int(cfg.secondary_line_pattern)
            program.stipple_phase = int(cfg.secondary_line_shift)

            # Pass 1 — opaque fragments only, depth writes enabled.
            # The shader discards any fragment whose final alpha < 0.999 so only
            # fully-opaque tiles and lines write to the depth buffer.
            GL.glDepthMask(GL.GL_TRUE)
            program.opaque_pass = 1
            GL.glBindVertexArray(self._vao)
            GL.glDrawElements(GL.GL_TRIANGLES, self._n, GL.GL_UNSIGNED_INT, None)
            GL.glBindVertexArray(0)

            # Pass 2 — transparent fragments only, depth writes disabled so they
            # blend correctly without corrupting the depth buffer.
            GL.glDepthMask(GL.GL_FALSE)
            program.opaque_pass = 0
            GL.glBindVertexArray(self._vao)
            GL.glDrawElements(GL.GL_TRIANGLES, self._n, GL.GL_UNSIGNED_INT, None)
            GL.glBindVertexArray(0)

            GL.glDepthMask(GL.GL_TRUE)
            GL.glDisable(GL.GL_MULTISAMPLE)
