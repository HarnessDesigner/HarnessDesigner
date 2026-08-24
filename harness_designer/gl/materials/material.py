# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import numpy as np

from ... import color as _color
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ..shaders import program as _shader_program


class GLMaterial:
    """Base Material properties for Phong shading"""

    _ambient = (0.2, 0.2, 0.2)

    # color is the "color" we tend to think of, tends to be white for metals
    _diffuse = (0.8, 0.8, 0.8)

    # plastics white, metals darker color
    _specular = (0.5, 0.5, 0.5)

    # light emitting like LED's
    _emissive = (0.0, 0.0, 0.0, 0.0)

    # polished metals has the highest shine, rubber type materials will have a
    # really low shine. plastics are in between
    _shine = 32.0  # 0.0 to 128.0

    _cl_ambient = 0.2
    _cl_diffuse = 0.8
    _cl_specular = 0.5
    _cl_shininess = 32.0
    _cl_metallic = 0.0
    _cl_roughness = 0.5
    _cl_reflectivity = 0.5
    _cl_ior = 0.5

    @_check_types.do
    def __init__(self, color: _color.Color):
        """Initialise the :class:`GLMaterial` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param color: Value for ``color``.
        :type color: :class:`_color.Color`
        """
        self._color = color

        a = color.rgba_scalar[-1]
        self._is_opaque = a == 1.0

        self.ambient = np.array(self._ambient + (a,), dtype=np.float32)
        self.diffuse = np.array(self._diffuse + (a,), dtype=np.float32)
        self.specular = np.array(self._specular + (a,), dtype=np.float32)
        self.shininess = self._shine
        self.emissive = np.array(self._emissive, dtype=np.float32)

    @property
    @_check_types.do
    def cl_array(self):
        """Return the cl array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        r, g, b, a = self._color.rgba_scalar

        return np.array(
            [r, g, b, self._cl_ambient, self._cl_diffuse, self._cl_specular,
             self._cl_shininess, self._cl_metallic, self._cl_roughness,
             self._cl_reflectivity, a, self._cl_ior], dtype=np.float32)

    @property
    @_check_types.do
    def color_scalar(self):
        """Return the color scalar.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._color.rgba_scalar

    @property
    @_check_types.do
    def is_opaque(self):
        """Return the is opaque.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._is_opaque

    @_check_types.do
    def set(self, program: _Union["_shader_program.FacesProgram", "_shader_program.EdgesProgram"]):
        """Push this material's uniforms onto the given (already-bound) program.

        :param program: The faces or edges program currently bound via
            ``with program:``.
        """

        # if self.is_opaque:
        #     GL.glDepthMask(GL.GL_TRUE)
        #
        # else:
        #     GL.glDepthMask(GL.GL_FALSE)

        program.material_ambient = self.ambient
        program.material_diffuse = self.diffuse
        program.material_specular = self.specular
        program.material_shininess = self.shininess
        program.material_emissive = self.emissive

        if not hasattr(type(program), "emissive_rim_power"):
            return

        if (
            self.emissive[0] != 0.0 or
            self.emissive[1] != 0.0 or
            self.emissive[2] != 0.0
        ):
            rim = sum(float(str(v)) for v in self.emissive[:-1].tolist()) * 2
            program.emissive_rim_power = rim
            program.emissive_rim_intensity = rim
        else:
            program.emissive_rim_power = 0.0
            program.emissive_rim_intensity = 0.0
