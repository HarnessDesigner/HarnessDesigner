# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from OpenGL import GL
import numpy as np
import ctypes


if TYPE_CHECKING:
    from . import canvas as _canvas


class Floor:
    """Procedural floor/grid plane rendered entirely in the shader.

    A single two-triangle plane mesh covers the configured floor area.  All
    visual detail (checkerboard tiles, solid major grid lines, dotted minor
    grid lines) is computed in the fragment shader so that no deprecated
    fixed-function primitives (GL_QUADS, GL_LINE_STIPPLE) are required.
    """

    def __init__(self, canvas: "_canvas.Canvas", floor_program):
        self.canvas = canvas
        self.config = canvas.config

        self._vao = None
        self._vbo = None
        self._vertex_count = 0

        self.projection_loc = GL.glGetUniformLocation(floor_program, "projection")
        self.view_loc = GL.glGetUniformLocation(floor_program, "view")
        self.u_grid_step_loc = GL.glGetUniformLocation(floor_program, "u_grid_step")
        self.u_primary_color_loc = GL.glGetUniformLocation(floor_program, "u_primary_color")
        self.u_secondary_color_loc = GL.glGetUniformLocation(floor_program, "u_secondary_color")
        self.u_grid_enable_loc = GL.glGetUniformLocation(floor_program, "u_grid_enable")

    def _initialize_grid(self):
        """Upload a simple two-triangle plane to the GPU.

        The plane covers the full floor extent (±distance) at ground_height.
        All grid/checkerboard detail is produced by the shader at render time.
        """
        size = float(self.config.floor.distance)
        ground_height = float(self.config.floor.ground_height)

        # Two triangles forming a quad in the XZ plane at ground_height
        vertices = np.array([
            -size, ground_height, -size,
            -size, ground_height,  size,
             size, ground_height,  size,
            -size, ground_height, -size,
             size, ground_height,  size,
             size, ground_height, -size,
        ], dtype=np.float32)

        with self.canvas.context:
            vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(vao)

            vbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(
                GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW
            )

            # layout(location = 0) in vec3 in_position
            GL.glEnableVertexAttribArray(0)
            GL.glVertexAttribPointer(
                0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0)
            )

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
            GL.glBindVertexArray(0)

        return vao, vbo, 6

    def set(self, flag):
        """(Re-)build the floor plane when *flag* is True, or tear it down."""
        if self._vao is not None:
            with self.canvas.context:
                GL.glDeleteVertexArrays(1, [self._vao])
                GL.glDeleteBuffers(1, [self._vbo])
            self._vao = None
            self._vbo = None
            self._vertex_count = 0

        if flag:
            self._vao, self._vbo, self._vertex_count = self._initialize_grid()

        self.canvas.Refresh(False)

    def render(self, floor_program):
        """Render the procedural floor plane."""
        if not self.config.floor.enable:
            return

        if self._vao is None:
            return

        projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        view_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

        GL.glUseProgram(floor_program)

        GL.glUniformMatrix4fv(
            self.projection_loc, 1, GL.GL_FALSE, projection_matrix
        )
        GL.glUniformMatrix4fv(
            self.view_loc, 1, GL.GL_FALSE, view_matrix
        )
        GL.glUniform1f(
            self.u_grid_step_loc, float(self.config.floor.grid.size)
        )
        GL.glUniform4fv(
            self.u_primary_color_loc, 1,
            np.array(self.config.floor.grid.primary_color, dtype=np.float32)
        )
        GL.glUniform4fv(
            self.u_secondary_color_loc, 1,
            np.array(self.config.floor.grid.secondary_color, dtype=np.float32)
        )
        GL.glUniform1i(
            self.u_grid_enable_loc, int(self.config.floor.grid.enable)
        )

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)

        GL.glBindVertexArray(self._vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._vertex_count)
        GL.glBindVertexArray(0)

        GL.glDepthMask(GL.GL_TRUE)
        GL.glUseProgram(0)
