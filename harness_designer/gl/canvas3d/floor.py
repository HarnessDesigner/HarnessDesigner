from typing import TYPE_CHECKING

from OpenGL import GL
import numpy as np
import ctypes


if TYPE_CHECKING:
    from . import canvas as _canvas


class Floor:

    def __init__(self, canvas: "_canvas.Canvas", floor_program):
        self.canvas = canvas
        self._floor_program = floor_program

        self.grid_vbo = None
        self.grid_vertex_count = 0

        self.stipple_vbo = None
        self.stipple_vertex_count = 0

        self.solid_vbo = None
        self.solid_vertex_count = 0

        self.config = canvas.config

    def _initialize_grid(self):
        """
        Compute the "Floor" and store it in the graphics adapter memory.

        This allows for a super fast render of the floor.

        :return:
        """
        even_color = self.config.floor.grid.primary_color
        ground_height = self.config.floor.ground_height
        size = self.config.floor.distance
        step = self.config.floor.grid.size

        def _get_vbo(verts, clrs):
            # Flatten the data
            verts = np.array(verts, dtype=np.float32).flatten()
            clrs = np.array(clrs, dtype=np.float32).flatten()

            # Combine vertices and colors into one array to pass to OpenGL
            v_data = np.concatenate((verts, clrs))

            # Calculate the number of vertices (for rendering)
            verts_count = len(verts) / 3

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            vbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, v_data.nbytes,
                            v_data, GL.GL_STATIC_DRAW)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            return vbo, int(verts_count)

        if self.config.floor.grid.enable:
            # Grid configuration

            odd_color = self.config.floor.grid.secondary_color

            # Precompute vertices and colors
            vertices = []
            colors = []

            for x in range(-size, size, step):
                for y in range(-size, size, step):
                    # Alternate coloring for checkerboard effect
                    is_even = ((x // step) + (y // step)) % 2 == 0
                    color = even_color if is_even else odd_color

                    # Each quad consists of 4 vertices
                    vertices.extend([
                        [x, ground_height, y], [x, ground_height, y + step],
                        [x + step, ground_height, y + step], [x + step, ground_height, y]])

                    # Each vertex has the same color for the quad
                    colors.extend([color] * 4)
        else:
            vertices = [[size, ground_height, size], [size, ground_height, -size],
                        [-size, ground_height, -size], [-size, ground_height, size]]

            colors = [even_color] * 4

        grid_vbo, grid_vertex_count = _get_vbo(vertices, colors)

        sstep = step / 5.0
        y1 = ground_height + 0.1
        y2 = ground_height + 0.15

        def _frange(start, stop, inc):
            value = start
            while value < stop:
                yield value
                value += inc

        stipple_lines = []
        solid_lines = []

        stipple_colors = []
        solid_colors = []

        for i in _frange(-size, size + 1, sstep):
            if not i % step:
                solid_colors.extend([0.65, 0.65, 0.65, 1.0] * 4)
                solid_lines.extend([[i, y2, size], [i, y2, -size],
                                    [size, y2, i], [-size, y2, i]])
            else:
                stipple_colors.extend([0.35, 0.35, 0.35, 1.0] * 4)
                stipple_lines.extend([[i, y1, size], [i, y1, -size],
                                      [size, y1, i], [-size, y1, i]])

        stipple_vbo, stipple_vertex_count = _get_vbo(stipple_lines, stipple_colors)
        solid_vbo, solid_vertex_count = _get_vbo(solid_lines, solid_colors)

        return (grid_vbo, grid_vertex_count,
                stipple_vbo, stipple_vertex_count,
                solid_vbo, solid_vertex_count)

    def set(self, flag):
        with (self.canvas.context):
            if self.grid_vbo is not None:
                try:
                    GL.glDeleteVertexArrays(1, [self.grid_vbo])
                except:  # NOQA
                    pass

                try:
                    GL.glDeleteBuffers(1, [self.stipple_vbo])
                except:  # NOQA
                    pass

                try:
                    GL.glDeleteBuffers(1, [self.solid_vbo])
                except:  # NOQA
                    pass

                self.grid_vbo = None
                self.stipple_vbo = None
                self.solid_vbo = None

            if flag:
                (
                    self.grid_vbo, self.grid_vertex_count,
                    self.stipple_vbo, self.stipple_vertex_count,
                    self.solid_vbo, self.solid_vertex_count
                ) = self._initialize_grid()

        self.canvas.Refresh(False)

    def render(self, floor_program):
        """Render the precomputed grid using the floor shader program."""

        if not self.config.floor.enable:
            return

        # Get the current projection and view matrices set by the camera
        projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        view_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

        GL.glUseProgram(floor_program)

        projection_loc = GL.glGetUniformLocation(floor_program, "projection")
        view_loc = GL.glGetUniformLocation(floor_program, "view")
        GL.glUniformMatrix4fv(projection_loc, 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, view_matrix)

        # type_ is either GL.GL_LINES or GL.GL_QUADS
        def _draw_vbo(vbo, count, type_):
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)

            # Colors start immediately after all position data: count vertices × 3 position floats × 4 bytes per float
            color_offset = count * 3 * 4  # byte offset to the color block

            # Layout 0: position (vec3)
            GL.glEnableVertexAttribArray(0)
            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))

            # Layout 1: color (vec4)
            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(1, 4, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(color_offset))

            GL.glDrawArrays(type_, 0, count)

            GL.glDisableVertexAttribArray(1)
            GL.glDisableVertexAttribArray(0)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # enable blending and disable the depth mask to remove the moiré that
        # occurs from the grid lines.
        # https://en.wikipedia.org/wiki/Moir%C3%A9_pattern
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)

        # draw grid floor
        _draw_vbo(self.grid_vbo, self.grid_vertex_count, GL.GL_QUADS)

        if self.config.floor.grid.enable:
            # draw grid dashed lines
            GL.glLineStipple(1, 0xFF00)
            GL.glEnable(GL.GL_LINE_STIPPLE)
            _draw_vbo(self.stipple_vbo, self.stipple_vertex_count, GL.GL_LINES)
            GL.glDisable(GL.GL_LINE_STIPPLE)

            # draw grid solid lines
            _draw_vbo(self.solid_vbo, self.solid_vertex_count, GL.GL_LINES)

        GL.glDepthMask(GL.GL_TRUE)
        GL.glUseProgram(0)
