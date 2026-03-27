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

    # polished metals has the highest shine, rubber type materials will have a
    # really low shine. plastics are in between
    _shine = 32.0  # 0.0 to 128.0

    def __init__(self, color: _color.Color):
        self._color = color

        a = color.rgba_scalar[-1]
        self._is_opaque = a == 1.0

        self.ambient = np.array(self._ambient + (a,), dtype=np.float32)
        self.diffuse = np.array(self._diffuse + (a,), dtype=np.float32)
        self.specular = np.array(self._specular + (a,), dtype=np.float32)
        self.shininess = self._shine

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

        GL.glUniform4fv(ambient, 1, self.ambient)
        GL.glUniform4fv(diffuse, 1, self.diffuse)
        GL.glUniform4fv(specular, 1, self.specular)
        GL.glUniform1f(shininess, self.shininess)
