# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas_base as _canvas_base


class SceneLight:
    """
    Manages the main scene lighting uniforms
    """
    
    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase", program):
        """
        Initialise the :class:`SceneLight` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """

        self.canvas = canvas
        self.config = self.canvas.config.lighting

        self._lightPosition = GL.glGetUniformLocation(program, "lightPosition")
        self._lightAmbient = GL.glGetUniformLocation(program, "lightAmbient")
        self._lightDiffuse = GL.glGetUniformLocation(program, "lightDiffuse")
        self._lightSpecular = GL.glGetUniformLocation(program, "lightSpecular")

    @_check_types.do
    def render(self, program):  # NOQA
        """
        Set the light uniforms in the shader

        Binds *program* itself rather than assuming the caller already
        left it current -- _set_shader_programs() (the caller, in
        canvas_base.py) cycles through faces/edges/vertices in sequence
        and leaves the vertices program bound at the end, not faces,
        which is what self._lightPosition etc. were queried against in
        __init__. Setting a uniform location that doesn't belong to the
        currently-bound program raises GL_INVALID_OPERATION.
        """

        position = self.canvas.camera.position.as_numpy
        ambient = np.array(self.config.ambient, dtype=np.float32)
        diffuse = np.array(self.config.diffuse, dtype=np.float32)
        specular = np.array(self.config.specular, dtype=np.float32)

        GL.glUseProgram(program)
        GL.glUniform3fv(self._lightPosition, 1, position)
        GL.glUniform4fv(self._lightAmbient, 1, ambient)
        GL.glUniform4fv(self._lightDiffuse, 1, diffuse)
        GL.glUniform4fv(self._lightSpecular, 1, specular)
