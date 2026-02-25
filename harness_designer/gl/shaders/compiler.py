from OpenGL import GL


def compile(source, shader_type):  # NOQA
    """Compile a shader"""
    shader = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader, source)
    GL.glCompileShader(shader)

    if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
        error = GL.glGetShaderInfoLog(shader).decode()
        raise RuntimeError(f"Shader compilation failed: {error}")

    return shader
