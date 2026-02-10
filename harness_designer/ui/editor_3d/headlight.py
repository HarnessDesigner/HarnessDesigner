import math

from OpenGL import GL

from . import config as _config


Config = _config.Config.headlight


class Headlight:

    def __init__(self, canvas):
        self.canvas = canvas
        self.camera = canvas.camera
        self.light_direction = [0.0, 0.0, 0.0]

        canvas.camera.position.bind(self.__update_position)
        canvas.camera.eye.bind(self.__update_eye)

    def __update_light(self):
        direction = self.canvas.camera.position - self.canvas.camera.eye
        magnitude = math.sqrt(sum(d ** 2 for d in direction))
        self.light_direction = [d / magnitude for d in direction]

    def __update_position(self, _):
        self.__update_light()

    def __update_eye(self, _):
        self.__update_light()

    def __call__(self):
        # Set spotlight position and direction
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT1)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, list(self.canvas.camera.eye.as_float) + [1.0])  # Positional light (headlight)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPOT_DIRECTION, self.light_direction)  # Spotlight direction

        # FLASHLIGHT SETTINGS:
        GL.glLightf(GL.GL_LIGHT1, GL.GL_SPOT_CUTOFF, Config.cutoff)  # Narrow beam with a cone angle of 15 degrees
        GL.glLightf(GL.GL_LIGHT1, GL.GL_SPOT_EXPONENT, Config.dissipate)  # Sharper falloff near the cutoff

        # Intensity falls off smoothly as the light exits the beam
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, Config.color)  # Strong white light inside the beam
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, Config.color)  # Specular highlights


