# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Textured-quad shader -- draws a single GL texture (sampled from
``imageTexture``, texture unit 0) across a unit quad, unlit, alpha-tested
(``discard`` below 1% alpha rather than blended, so a texture with a hard
transparent edge doesn't leave a translucent halo).

Ported from the proven ``TextureProgram`` in scratches/pegboard_spreadsheet_
widget/gl_spreadsheet_test.py (built and visually verified there for the
wire-icon column) -- same GLSL, same compile/link pattern as every other
shader in this package, just placed here now that it has a second real
consumer: ``objects.objects_pegboard.pegboard_table.PegboardTable`` renders
a peg-board floating wire table by capturing a hidden ``QMdiSubWindow`` to a
QImage and uploading it as this shader's texture each time its content
changes (see that module for the capture side).
"""

import os
from OpenGL import GL

from .. import compiler as _compiler


BASE_PATH = os.path.abspath(os.path.dirname(__file__))


def compile_program():
    """
    Compile and link the texture shader program.
    """

    vertex = open(os.path.join(BASE_PATH, 'vertex.vert'), 'r', encoding='ascii').read()
    fragment = open(os.path.join(BASE_PATH, 'fragment.frag'), 'r', encoding='ascii').read()

    vertex_shader = _compiler.compile(vertex, GL.GL_VERTEX_SHADER)
    fragment_shader = _compiler.compile(fragment, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Texture program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(fragment_shader)

    return program
