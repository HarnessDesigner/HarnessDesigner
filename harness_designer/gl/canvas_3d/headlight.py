# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import numpy as np
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas as _canvas
    from .. import shaders as _shaders


class Headlight:
    """
    Represent a headlight in :mod:`harness_designer.gl.canvas3d.headlight`.
    Always targets ``shaders.faces``.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
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

    @_check_types.do
    def __update(self, _):
        """
        Execute the update operation.
        """

        direction = self.canvas.camera.focal_position - self.canvas.camera.position
        magnitude = math.sqrt(sum(d ** 2 for d in direction))
        self.light_direction = [d / magnitude for d in direction]

    @_check_types.do
    def set(self, shaders: "_shaders.ShaderProgram"):
        """
        Push the headlight uniforms onto the faces program.
        """

        program = shaders.faces

        with self.canvas.context:
            with program:
                program.headlight_position = self.canvas.camera.position.as_numpy
                program.headlight_direction = self.light_direction
                program.headlight_diffuse = np.array(self.config.color, dtype=np.float32)
                program.headlight_diameter = math.radians(self.config.cutoff)
                program.headlight_enabled = self.config.enable

