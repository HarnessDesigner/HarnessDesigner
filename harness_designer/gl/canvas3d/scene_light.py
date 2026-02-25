import numpy as np
from OpenGL import GL

from ... import config as _config


Config = _config.Config.editor3d.lighting


class SceneLight:
    """Manages the main scene lighting uniforms"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.config = self.canvas.config.lighting if hasattr(self.canvas.config, 'lighting') else None
        
        # Default light settings if config doesn't exist
        self.position = np.array([100.0, 100.0, 100.0], dtype=np.float32)
        self.ambient = np.array([0.2, 0.2, 0.2, 1.0], dtype=np.float32)
        self.diffuse = np.array([0.8, 0.8, 0.8, 1.0], dtype=np.float32)
        self.specular = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        
        if self.config:
            if hasattr(self.config, 'position'):
                self.position = np.array(self.config.position, dtype=np.float32)
            if hasattr(self.config, 'ambient'):
                self.ambient = np.array(self.config.ambient, dtype=np.float32)
            if hasattr(self.config, 'diffuse'):
                self.diffuse = np.array(self.config.diffuse, dtype=np.float32)
            if hasattr(self.config, 'specular'):
                self.specular = np.array(self.config.specular, dtype=np.float32)
    
    def set_uniforms(self, shader_program):
        """Set the light uniforms in the shader"""
        lightPosition = GL.glGetUniformLocation(shader_program, "lightPosition")
        lightAmbient = GL.glGetUniformLocation(shader_program, "lightAmbient")
        lightDiffuse = GL.glGetUniformLocation(shader_program, "lightDiffuse")
        lightSpecular = GL.glGetUniformLocation(shader_program, "lightSpecular")
        
        GL.glUniform3fv(lightPosition, 1, self.position)
        GL.glUniform4fv(lightAmbient, 1, self.ambient)
        GL.glUniform4fv(lightDiffuse, 1, self.diffuse)
        GL.glUniform4fv(lightSpecular, 1, self.specular)
