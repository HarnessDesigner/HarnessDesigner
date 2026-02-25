import numpy as np
from OpenGL import GL

from ... import config as _config


Config = _config.Config.editor3d.lighting


class SceneLight:
    """Manages the main scene lighting uniforms"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.config = self.canvas.config.lighting

    def set(self, shader_program):
        """Set the light uniforms in the shader"""

        position = np.array(self.config.position, dtype=np.float32)
        ambient = np.array(self.config.ambient, dtype=np.float32)
        diffuse = np.array(self.config.diffuse, dtype=np.float32)
        specular = np.array(self.config.specular, dtype=np.float32)

        lightPosition = GL.glGetUniformLocation(shader_program, "lightPosition")
        lightAmbient = GL.glGetUniformLocation(shader_program, "lightAmbient")
        lightDiffuse = GL.glGetUniformLocation(shader_program, "lightDiffuse")
        lightSpecular = GL.glGetUniformLocation(shader_program, "lightSpecular")
        
        GL.glUniform3fv(lightPosition, 1, position)
        GL.glUniform4fv(lightAmbient, 1, ambient)
        GL.glUniform4fv(lightDiffuse, 1, diffuse)
        GL.glUniform4fv(lightSpecular, 1, specular)
