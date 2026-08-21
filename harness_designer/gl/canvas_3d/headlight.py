# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import numpy as np
from OpenGL import GL
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas as _canvas


class Headlight:
    """
    Represent a headlight in :mod:`harness_designer.gl.canvas3d.headlight`.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", program):
        """
        Initialise the :class:`Headlight` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """

        self.canvas = canvas
        self.camera = canvas.camera
        self.config = self.canvas.config.headlight
        self.light_direction = [0.0, 0.0, 0.0]

        canvas.camera.position.bind(self.__update)
        canvas.camera.focal_position.bind(self.__update)

        with self.canvas.context:
            GL.glUseProgram(program)
            self._headlightPosition = GL.glGetUniformLocation(program, "headlightPosition")
            self._headlightDirection = GL.glGetUniformLocation(program, "headlightDirection")
            self._headlightDiffuse = GL.glGetUniformLocation(program, "headlightDiffuse")
            self._headlightDiameter = GL.glGetUniformLocation(program, "headlightDiameter")
            self._headlightEnabled = GL.glGetUniformLocation(program, "headlightEnabled")
            GL.glUseProgram(0)

    @_check_types.do
    def __update(self, _):
        """
        Execute the update operation.
        """

        direction = self.canvas.camera.focal_position - self.canvas.camera.position
        magnitude = math.sqrt(sum(d ** 2 for d in direction))
        self.light_direction = [d / magnitude for d in direction]

    @_check_types.do
    def set(self, program):
        """
        Call the instance.

        :param program: Value for ``shader_program``.
        :type program: UNKNOWN
        """

        with self.canvas.context:
            GL.glUseProgram(program)
            GL.glUniform3fv(self._headlightPosition, 1, self.canvas.camera.position.as_numpy)
            GL.glUniform3fv(self._headlightDirection, 1, self.light_direction)
            GL.glUniform4fv(self._headlightDiffuse, 1, np.array(self.config.color, dtype=np.float32))

            GL.glUniform1f(self._headlightDiameter, math.radians(self.config.cutoff))
            GL.glUniform1i(self._headlightEnabled, self.config.enable)
            GL.glUseProgram(0)

