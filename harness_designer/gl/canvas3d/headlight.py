from typing import TYPE_CHECKING

import math
import numpy as np

from OpenGL import GL

if TYPE_CHECKING:
    from . import canvas as _canvas


class Headlight:

    def __init__(self, canvas: "_canvas.Canvas"):
        self.canvas = canvas
        self.camera = canvas.camera
        self.config = self.canvas.config.headlight
        self.light_direction = [0.0, 0.0, 0.0]

        canvas.camera.position.bind(self.__update)
        canvas.camera.focal_position.bind(self.__update)

    def __update_light(self):
        direction = self.canvas.camera.focal_position - self.canvas.camera.position
        magnitude = math.sqrt(sum(d ** 2 for d in direction))
        self.light_direction = [d / magnitude for d in direction]

    def __update(self, _):
        self.__update_light()

    def __call__(self, shader_program):
        headlightPosition = GL.glGetUniformLocation(shader_program, "headlightPosition")
        headlightDirection = GL.glGetUniformLocation(shader_program, "headlightDirection")
        headlightDiffuse = GL.glGetUniformLocation(shader_program, "headlightDiffuse")
        headlightDiameter = GL.glGetUniformLocation(shader_program, "headlightDiameter")
        headlightEnabled = GL.glGetUniformLocation(shader_program, "headlightEnabled")

        GL.glUniform3fv(headlightPosition, 1, self.canvas.camera.position.as_numpy)
        GL.glUniform3fv(headlightDirection, 1, self.light_direction)
        GL.glUniform4fv(headlightDiffuse, 1, np.array(self.config.color, dtype=np.float32))

        GL.glUniform1f(headlightDiameter, math.radians(self.config.cutoff))
        GL.glUniform1i(headlightEnabled, self.config.enable)
        #
        # # Set spotlight position and direction
        # GL.glEnable(GL.GL_LIGHTING)
        # GL.glEnable(GL.GL_LIGHT1)
        # GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, list(self.canvas.camera.eye.as_float) + [1.0])  # Positional light (headlight)
        # GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPOT_DIRECTION, )  # Spotlight direction
        #
        # # FLASHLIGHT SETTINGS:
        # GL.glLightf(GL.GL_LIGHT1, GL.GL_SPOT_CUTOFF, Config.cutoff)  # Narrow beam with a cone angle of 15 degrees
        # GL.glLightf(GL.GL_LIGHT1, GL.GL_SPOT_EXPONENT, Config.dissipate)  # Sharper falloff near the cutoff
        #
        # # Intensity falls off smoothly as the light exits the beam
        # GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, Config.color)  # Strong white light inside the beam
        # GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, Config.color)  # Specular highlights


