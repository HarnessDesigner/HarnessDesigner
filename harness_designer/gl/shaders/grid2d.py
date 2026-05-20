# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from OpenGL import GL
from . import compiler as _compiler


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec2 in_position;   // world-space XY from VBO

uniform mat4 projection;
uniform mat4 view;
uniform float pointSize;   // set by Grid._draw_layer

void main() {
    gl_Position  = projection * view * vec4(in_position, 0.0, 1.0);
    gl_PointSize = pointSize;
}
"""


FRAGMENT_SHADER = """
#version 330 core

out vec4 FragColor;

uniform vec4 dotColor;

void main() {
    // Circular dot with soft anti-aliased edge
    vec2  coord = gl_PointCoord - vec2(0.5);
    float dist  = length(coord);

    if (dist > 0.5) {
        discard;
    }

    float alpha = smoothstep(0.5, 0.3, dist) * dotColor.a;
    FragColor   = vec4(dotColor.rgb, alpha);
}
"""


def compile_program() -> int:
    """Compile and link the 2D dot-grid shader program."""
    vs = _compiler.compile(VERTEX_SHADER,   GL.GL_VERTEX_SHADER)
    fs = _compiler.compile(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vs)
    GL.glAttachShader(program, fs)
    GL.glLinkProgram(program)

    GL.glDeleteShader(vs)
    GL.glDeleteShader(fs)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"2D grid shader linking failed: {error}")

    return program
