# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from OpenGL import GL
from . import compiler as _compiler


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec2 in_position;   // world-space XY, one full-viewport quad

uniform mat4 projection;

out vec2 vWorld;

void main() {
    vWorld = in_position;
    gl_Position = projection * vec4(in_position, 0.0, 1.0);
}
"""


FRAGMENT_SHADER = """
#version 330 core

in vec2 vWorld;

out vec4 FragColor;

uniform float uSpacing;        // current world-space dot spacing -- see gl.floor.Floor._current_spacing
uniform float uWorldPerPixel;  // converts a pixel dot radius to world units
uniform vec4 uDotColor;

// Procedural dot grid: computed entirely from world position, no precomputed
// per-dot vertex data. Single tier only -- gl.floor.Floor._current_spacing
// already picks whichever power-of-2 spacing keeps this tier's own
// on-screen spacing within [target/2, target] (see its own docstring for
// why), so there is nothing left for the shader itself to decide.

void main() {
    float radius = 2.0 * 0.5 * uWorldPerPixel;  // fixed on-screen dot size (pixels), at current zoom

    vec2 cell = fract(vWorld / uSpacing);
    vec2 d = min(cell, 1.0 - cell) * uSpacing;
    float dist = length(d);
    float alpha = (1.0 - smoothstep(radius * 0.6, radius, dist)) * uDotColor.a;

    if (alpha < 0.003) {
        discard;
    }

    FragColor = vec4(uDotColor.rgb, alpha);
}
"""


def compile_program() -> int:
    """Compile and link the procedural 2D dot-grid shader program."""
    vs = _compiler.compile(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
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
