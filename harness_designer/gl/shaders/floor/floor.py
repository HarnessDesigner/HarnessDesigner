# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
from OpenGL import GL

from .. import compiler as _compiler


BASE_PATH = os.path.abspath(os.path.dirname(__file__))


def compile_program():
    """
    Compile and link the procedural floor shader.
    """

    vertex = open(os.path.join(BASE_PATH, 'vertex.vert'), 'r', encoding='ascii').read()
    fragment = open(os.path.join(BASE_PATH, 'fragment.frag'), 'r', encoding='ascii').read()

    program = GL.glCreateProgram()

    vertex_shader = _compiler.compile(vertex,   GL.GL_VERTEX_SHADER)
    fragment_shader = _compiler.compile(fragment, GL.GL_FRAGMENT_SHADER)

    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f'Floor program linking failed: {error}')

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(fragment_shader)

    return program
