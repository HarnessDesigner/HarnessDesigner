from OpenGL import GL

import numpy as np

from ... import color as _color


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

    def __init__(self, color: _color.Color):
        self._color = color

        a = color.rgba_scalar[-1]
        self._is_opaque = a == 1.0

        self.ambient = np.array(self._ambient + (a,), dtype=np.float32)
        self.diffuse = np.array(self._diffuse + (a,), dtype=np.float32)
        self.specular = np.array(self._specular + (a,), dtype=np.float32)
        self.shininess = self._shine
        self.emissive = np.array(self._emissive, dtype=np.float32)

    @property
    def cl_array(self):
        r, g, b, a = self._color.rgba_scalar

        return np.array(
            [r, g, b, self._cl_ambient, self._cl_diffuse, self._cl_specular,
             self._cl_shininess, self._cl_metallic, self._cl_roughness,
             self._cl_reflectivity, a, self._cl_ior], dtype=np.float32)

    @property
    def color_scalar(self):
        return self._color.rgba_scalar

    @property
    def is_opaque(self):
        return self._is_opaque

    def set(self, shader_program):
        ambient = GL.glGetUniformLocation(shader_program, "materialAmbient")
        diffuse = GL.glGetUniformLocation(shader_program, "materialDiffuse")
        specular = GL.glGetUniformLocation(shader_program, "materialSpecular")
        shininess = GL.glGetUniformLocation(shader_program, "materialShininess")
        emissive = GL.glGetUniformLocation(shader_program, "materialEmissive")
        emissive_rim_power = GL.glGetUniformLocation(shader_program, "emissiveRimPower")
        emissive_rim_intensity = GL.glGetUniformLocation(shader_program, "emissiveRimIntensity")

        GL.glUniform4fv(ambient, 1, self.ambient)
        GL.glUniform4fv(diffuse, 1, self.diffuse)
        GL.glUniform4fv(specular, 1, self.specular)
        GL.glUniform1f(shininess, self.shininess)
        GL.glUniform4fv(emissive, 1, self.emissive)

        if (
            self.emissive[0] != 0.0 or
            self.emissive[1] != 0.0 or
            self.emissive[2] != 0.0
        ):
            GL.glUniform1f(emissive_rim_power, sum(self.emissive[:-1].tolist()) * 2)
            GL.glUniform1f(emissive_rim_intensity, sum(self.emissive[:-1].tolist()) * 2)
        else:
            GL.glUniform1f(emissive_rim_power, 0.0)
            GL.glUniform1f(emissive_rim_intensity, 0.0)
