# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Procedural top-down dot grid, shared by the 2D schematic editor and the
peg board editor.

Replaces the previous CPU-precomputed-VBO-of-dots approach entirely: a
single small quad always sized to the current viewport is drawn, and the
fragment shader (``gl.shaders.grid2d``) computes every dot procedurally
from world position -- the same "one quad, all detail in the fragment
shader" technique ``gl.canvas3d.floor.Floor`` already uses for the 3D
floor grid, adapted for an orthographic top-down view (no perspective, so
screen-space scale is uniform everywhere and a single ``world_per_pixel``
value stands in for ``fwidth()``-style derivatives).

This eliminates the background-thread/Decimal-heavy dot-position
precompute (and the GL-context-timing bug that came with it) along with
any fixed extent limit -- the quad always covers the current viewport
exactly, so the grid is effectively infinite regardless of pan/zoom.

Public interface (``__init__(canvas)``, ``set(flag)``, ``render(zoom)``,
``grid_spacing`` attribute) is unchanged from the previous implementation,
so neither ``gl.canvas2d.canvas.Canvas`` nor
``gl.canvas_pegboard.canvas.Canvas`` need any changes.
"""

from typing import TYPE_CHECKING

import math

from OpenGL import GL
import numpy as np
import ctypes

from .. import shaders as _shaders


if TYPE_CHECKING:
    from . import canvas as _canvas


def nice_value(n: float) -> float:
    """Return the n'th value in the ``..., 1, 5, 10, 50, 100, 500, ...``
    sequence -- every group of 2 consecutive integers covers one decade
    (``1, 5``), so ``n`` and ``n+2`` differ by exactly 10x.

    Consecutive values always have an integer ratio (either x5 or x2), so
    every coarser value is guaranteed to be an exact multiple of the next
    finer one -- e.g. 5 is a multiple of 1, 10 of 5, 50 of 10. This is what
    keeps the "minor" (one-step-finer) dot tier a true subset of the
    "major" tier's dots -- every major dot is also a minor dot.

    A 3-per-decade ``1, 2, 5, 10, ...`` sequence was tried first (closer to
    smooth-graphing convention) but was rejected: the 2->5 step is a 2.5x
    ratio, not an integer, so minor dots at spacing 2 do NOT land on major
    dots at spacing 5 -- exactly the misalignment this scheme avoids.

    :param n: Sequence index (need not be an integer type, but should hold
        an integer value -- callers pass ``float`` for GLSL-parity).
    :type n: float
    :returns: The nice value at that index.
    :rtype: float
    """
    decade = math.floor(n / 2.0)
    idx = int(round(n - decade * 2.0))
    mult = (1.0, 5.0)[idx]

    return mult * (10.0 ** decade)


def nice_index_for(raw: float) -> float:
    """Return the sequence index (see :func:`nice_value`) of whichever nice
    value is closest to *raw* (by ratio -- i.e. nearest in log space, using
    the geometric mean between adjacent nice values as the switchover
    point).

    :param raw: Target (not-necessarily-nice) spacing.
    :type raw: float
    :returns: Sequence index suitable for :func:`nice_value`.
    :rtype: float
    """
    if raw <= 0.0:
        return 0.0

    decade = math.floor(math.log10(raw))
    frac = raw / (10.0 ** decade)

    if frac < math.sqrt(5.0):      # geometric mean of 1 and 5
        idx, dd = 0, decade
    elif frac < math.sqrt(50.0):   # geometric mean of 5 and 10
        idx, dd = 1, decade
    else:
        idx, dd = 0, decade + 1

    return float(dd * 2 + idx)


def _build_quad(left: float, right: float, bottom: float, top: float) -> np.ndarray:
    """Two triangles covering the given world-space rectangle, flat vec2 array."""
    return np.array([
        left, bottom,   right, bottom,   right, top,
        left, bottom,   right, top,      left, top,
    ], dtype=np.float32)


class Grid:
    """Procedural top-down dot grid."""

    def __init__(self, canvas: "_canvas.Canvas2D"):
        self.canvas = canvas
        self.config = canvas.config

        self.grid_spacing = 1.0

        self._program = None
        self._vao = None
        self._vbo = None

        self._loc_projection = None
        self._loc_zoom_ratio = None
        self._loc_distance = None
        self._loc_world_per_pixel = None
        self._loc_major_color = None
        self._loc_minor_color = None

    def _ensure_program(self):
        if self._program is not None:
            return

        self._program = _shaders.compile_grid2d_program()

        self._loc_projection = GL.glGetUniformLocation(self._program, "projection")
        self._loc_zoom_ratio = GL.glGetUniformLocation(self._program, "uZoomRatio")
        self._loc_distance = GL.glGetUniformLocation(self._program, "uDistance")
        self._loc_world_per_pixel = GL.glGetUniformLocation(self._program, "uWorldPerPixel")
        self._loc_major_color = GL.glGetUniformLocation(self._program, "uMajorColor")
        self._loc_minor_color = GL.glGetUniformLocation(self._program, "uMinorColor")

    def _build_gl_resources(self):
        verts = _build_quad(-1.0, 1.0, -1.0, 1.0)  # placeholder bounds, updated every render()

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
        """Enable or disable the grid, (re)building GPU resources as needed."""

        def _do(f):
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

                if f:
                    self._ensure_program()
                    self._vao, self._vbo = self._build_gl_resources()

            self.canvas.Refresh(False)

        from harness_designer import app as _app

        _app.CallAfter(_do, flag)

    def _current_major_spacing(self, distance: float) -> float:
        """Return the currently-displayed bold tier's spacing.

        Mirrors the fragment shader's ``niceValue(niceIndexFor(...))`` call
        exactly, evaluated once on the CPU so :attr:`grid_spacing` (read by
        ``Canvas.snap_to_grid``) reflects whatever is currently drawn as
        the bold tier -- the nearest "nice" 1/5 x 10^n value to
        ``distance / zoom_ratio``.
        """
        zoom_ratio = float(self.config.grid.zoom_ratio)
        raw = distance / zoom_ratio

        return nice_value(nice_index_for(raw))

    def render(self, zoom):
        """Draw the procedural grid, sized to exactly cover the current viewport."""

        if self._vao is None or not self.config.grid.enabled:
            return

        size = self.canvas.size
        if size is None:
            return

        width, height = size
        if width == 0 or height == 0:
            return

        camera = self.canvas.camera
        world_per_pixel = zoom / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = camera.x - half_width
        right = camera.x + half_width
        bottom = camera.y - half_height
        top = camera.y + half_height

        self.grid_spacing = self._current_major_spacing(zoom)

        with self.canvas.context:
            verts = _build_quad(left, right, bottom, top)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            GL.glBufferSubData(GL.GL_ARRAY_BUFFER, 0, verts.nbytes, verts)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

            near, far = -1.0, 1.0
            projection = np.array([
                [2.0 / (right - left), 0.0, 0.0, -(right + left) / (right - left)],
                [0.0, 2.0 / (top - bottom), 0.0, -(top + bottom) / (top - bottom)],
                [0.0, 0.0, -2.0 / (far - near), -(far + near) / (far - near)],
                [0.0, 0.0, 0.0, 1.0],
            ], dtype=np.float32)

            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glUseProgram(self._program)

            GL.glUniformMatrix4fv(self._loc_projection, 1, GL.GL_FALSE,
                                  np.ascontiguousarray(projection.T))
            GL.glUniform1f(self._loc_zoom_ratio, float(self.config.grid.zoom_ratio))
            GL.glUniform1f(self._loc_distance, float(zoom))
            GL.glUniform1f(self._loc_world_per_pixel, world_per_pixel)
            GL.glUniform4f(self._loc_major_color, 0.25, 0.25, 0.25, 1.0)
            GL.glUniform4f(self._loc_minor_color, 0.5, 0.5, 0.5, 1.0)

            GL.glBindVertexArray(self._vao)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)
            GL.glBindVertexArray(0)

            GL.glUseProgram(0)
