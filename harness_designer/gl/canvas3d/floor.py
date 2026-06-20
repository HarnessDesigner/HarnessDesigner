# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from OpenGL import GL
import numpy as np
import ctypes

if TYPE_CHECKING:
    from . import canvas as _canvas


# ═══════════════════════════════════════════════════════════════════════════════
#  Geometry
# ═══════════════════════════════════════════════════════════════════════════════

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

class Floor:
    """Procedural floor grid.

    Renders checkerboard tiles, major solid lines, and minor dashed lines
    entirely inside one fragment shader on a single large quad.

    This approach eliminates the orientation-dependent moiré that occurs
    when thin geometry quads are rasterised at sub-pixel widths, because
    the shader computes every line analytically using screen-space
    derivatives (fwidth) rather than relying on the rasteriser to hit
    thin geometry.

    Interface change vs the previous version
    ─────────────────────────────────────────
    __init__ and render now accept a single *program* instead of the
    previous (program_solid, program_dashed) pair.  Update call sites
    accordingly, and note that compile_program() in shader.py now also
    returns a single program object.
    """

    def __init__(self, canvas: '_canvas.Canvas', program):
        self.canvas = canvas

        with self.canvas.context:
            self._loc_mvp = GL.glGetUniformLocation(program, 'uMVP')
            self._loc_tile_sz = GL.glGetUniformLocation(program, 'uTileSize')
            self._loc_minor_sz = GL.glGetUniformLocation(program, 'uMinorSpacing')
            self._loc_color_a = GL.glGetUniformLocation(program, 'uColorA')
            self._loc_color_b = GL.glGetUniformLocation(program, 'uColorB')
            self._loc_maj_col = GL.glGetUniformLocation(program, 'uMajorColor')
            self._loc_min_col = GL.glGetUniformLocation(program, 'uMinorColor')
            self._loc_maj_w = GL.glGetUniformLocation(program, 'uMajorWidth')
            self._loc_min_w = GL.glGetUniformLocation(program, 'uMinorWidth')
            self._loc_stipple = GL.glGetUniformLocation(program, 'uStipplePattern')
            self._loc_has_minor = GL.glGetUniformLocation(program, 'uHasMinorGrid')
            self._loc_stipple_phase = GL.glGetUniformLocation(program, 'uStipplePhase')
            self._loc_opaque_pass = GL.glGetUniformLocation(program, 'uOpaquePass')

        self._vao = None
        self._vbo = None
        self._ebo = None
        self._n = None

        self.config = canvas.config.floor

    # ─────────────────────────────────────────────────────────────────────────

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

    def render(self, program):
        """Draw the procedural floor in a single pass."""

        if not self.config.enable or self._vao is None:
            return

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glUseProgram(program)

        # MVP ─────────────────────────────────────────────────────────────────
        GL.glUniformMatrix4fv(
            self._loc_mvp, 1, GL.GL_TRUE, self.canvas.camera.clip)

        # Grid dimensions ─────────────────────────────────────────────────────
        cfg = self.config.grid
        has_minor = 1 if cfg.enable else 0
        tile_size = cfg.size
        minor_sz = tile_size / (cfg.secondary_lines_per_tile + 1)

        GL.glUniform1f(self._loc_tile_sz,   tile_size)
        GL.glUniform1f(self._loc_minor_sz,  minor_sz)
        GL.glUniform1ui(self._loc_has_minor, has_minor)

        # Tile colours ────────────────────────────────────────────────────────
        pc = cfg.primary_color
        sc = cfg.secondary_color
        GL.glUniform4f(self._loc_color_a, *pc)
        GL.glUniform4f(self._loc_color_b, *sc)

        # Line colours ────────────────────────────────────────────────────────
        plc = cfg.primary_line_color
        slc = cfg.secondary_line_color
        GL.glUniform4f(self._loc_maj_col, *plc)
        GL.glUniform4f(self._loc_min_col, *slc)

        # Line widths ─────────────────────────────────────────────────────────
        GL.glUniform1f(self._loc_maj_w, cfg.primary_line_width)
        GL.glUniform1f(self._loc_min_w, cfg.secondary_line_width)

        # Dash parameters ─────────────────────────────────────────────────────
        GL.glUniform1ui(self._loc_stipple, int(cfg.secondary_line_pattern) & 0xFFFFFFFF)
        GL.glUniform1ui(self._loc_stipple_phase, int(cfg.secondary_line_shift))

        # Pass 1 — opaque fragments only, depth writes enabled.
        # The shader discards any fragment whose final alpha < 0.999 so only
        # fully-opaque tiles and lines write to the depth buffer.
        GL.glDepthMask(GL.GL_TRUE)
        GL.glUniform1i(self._loc_opaque_pass, 1)
        GL.glBindVertexArray(self._vao)
        GL.glDrawElements(GL.GL_TRIANGLES, self._n, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)

        # Pass 2 — transparent fragments only, depth writes disabled so they
        # blend correctly without corrupting the depth buffer.
        GL.glDepthMask(GL.GL_FALSE)
        GL.glUniform1i(self._loc_opaque_pass, 0)
        GL.glBindVertexArray(self._vao)
        GL.glDrawElements(GL.GL_TRIANGLES, self._n, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)

        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_MULTISAMPLE)
