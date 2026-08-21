# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from OpenGL import GL
import numpy as np
import ctypes
from ... import check_types as _check_types

if TYPE_CHECKING:
    from . import canvas_base as _canvas_base


# ═══════════════════════════════════════════════════════════════════════════════
#  Floor class
# ═══════════════════════════════════════════════════════════════════════════════

class FloorBase:
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

    @_check_types.do
    def __init__(self, canvas: '_canvas_base.CanvasBase', program):
        self.canvas = canvas

        self._vao = None
        self._vbo = None

        self.config = canvas.config.floor

    # ─────────────────────────────────────────────────────────────────────────

    @_check_types.do
    def _initialize_grid(self):
        raise NotImplementedError

    # ─────────────────────────────────────────────────────────────────────────

    @_check_types.do
    def set(self, flag):
        """
        Enable or disable the floor, rebuilding GPU resources as needed.
        """
        raise NotImplementedError

    # ─────────────────────────────────────────────────────────────────────────

    @_check_types.do
    def render(self, program):
        """
        Draw the procedural floor in a single pass.
        """
        raise NotImplementedError
