from OpenGL import GL

from . import compiler as _compiler


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_position;
layout(location = 1) in vec4 in_color;

uniform mat4 projection;
uniform mat4 view;

out vec4 vertColor;

void main() {
    gl_Position = projection * view * vec4(in_position, 1.0);
    vertColor = in_color;
}
"""

FRAGMENT_SHADER = """
#version 330 core

in vec4 vertColor;
out vec4 FragColor;

void main() {
    FragColor = vertColor;
}
"""


def compile_program():
    """Compile and link the floor shader program (per-vertex color, no lighting)."""
    vertex_shader = _compiler.compile(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
    fragment_shader = _compiler.compile(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Floor program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(fragment_shader)

    return program
