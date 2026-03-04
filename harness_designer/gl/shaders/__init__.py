from OpenGL import GL

from . import vertex as _vertex
from . import fragment as _fragment
from . import geometry as _geometry


def create_program():
    """Create shader program"""
    vertex_shader = _vertex.compile_shader()
    geometry_shader = _geometry.compile_shader()
    fragment_shader = _fragment.compile_shader()

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, geometry_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(geometry_shader)
    GL.glDeleteShader(fragment_shader)

    return program
