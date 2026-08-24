# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas_base as _canvas_base
    from .. import shaders as _shaders


class SceneLight:
    """
    Manages the main scene lighting uniforms. Always targets
    ``shaders.faces``.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase"):
        """
        Initialise the :class:`SceneLight` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """

        self.canvas = canvas
        self.config = self.canvas.config.lighting

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):  # NOQA
        """
        Set the light uniforms in the shader.
        """

        position = self.canvas.camera.position.as_numpy
        ambient = np.array(self.config.ambient, dtype=np.float32)
        diffuse = np.array(self.config.diffuse, dtype=np.float32)
        specular = np.array(self.config.specular, dtype=np.float32)

        program = shaders.faces

        with program:
            program.light_position = position
            program.light_ambient = ambient
            program.light_diffuse = diffuse
            program.light_specular = specular
