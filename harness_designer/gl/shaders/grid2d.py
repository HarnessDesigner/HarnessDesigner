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

uniform float uZoomRatio;      // target ratio of uDistance to displayed spacing
uniform float uDistance;       // camera.distance -- selects which tier is "major"
uniform float uWorldPerPixel;  // distance / 1000.0 -- converts a pixel dot radius to world units
uniform vec4 uMajorColor;
uniform vec4 uMinorColor;

// Procedural dot grid: computed entirely from world position, no precomputed
// per-dot vertex data (unlike the old CPU-generated VBO-of-points approach).
// Mirrors gl.shaders.floor's technique (single quad, all detail from the
// fragment shader) adapted for an orthographic top-down 2D view -- since
// there is no perspective here, screen-space scale is uniform everywhere,
// so uWorldPerPixel stands in for fwidth()-style derivatives.

float dotAlpha(vec2 world, float spacing, float radiusWorld) {
    vec2 cell = fract(world / spacing);
    vec2 d = min(cell, 1.0 - cell) * spacing;
    float dist = length(d);
    return 1.0 - smoothstep(radiusWorld * 0.6, radiusWorld, dist);
}

// "Nice" 1/5 x 10^n tick-spacing sequence -- every group of 2 consecutive
// integer indices covers one decade (1, 5), so n and n+2 differ by exactly
// 10x. Consecutive values always have an integer ratio (x5 or x2), which
// guarantees the minor (one-step-finer) dot tier is a true subset of the
// major tier's dots -- every major dot is also a minor dot. A 3-per-decade
// 1/2/5 sequence was tried first but rejected: its 2->5 step is a 2.5x
// ratio, not an integer, so minor dots at spacing 2 do not land on major
// dots at spacing 5. Mirrors gl.canvas2d.grid.nice_value()/nice_index_for()
// exactly (kept in sync by hand -- there is no shared source between GLSL
// and Python here).
float niceValue(float n) {
    float decade = floor(n / 2.0);
    float idx = n - decade * 2.0;
    float mult = idx < 0.5 ? 1.0 : 5.0;
    return mult * pow(10.0, decade);
}

float niceIndexFor(float raw) {
    if (raw <= 0.0) {
        return 0.0;
    }
    float decade = floor(log(raw) / log(10.0));
    float frac = raw / pow(10.0, decade);
    float idx;
    float dd;
    if (frac < 2.2360679) {        // sqrt(5) -- geometric mean of 1 and 5
        idx = 0.0; dd = decade;
    } else if (frac < 7.0710678) { // sqrt(50) -- geometric mean of 5 and 10
        idx = 1.0; dd = decade;
    } else {
        idx = 0.0; dd = decade + 1.0;
    }
    return dd * 2.0 + idx;
}

void main() {
    // Same rule the CPU side uses (nice_value(nice_index_for(distance /
    // zoom_ratio))), evaluated per-pixel -- identical for every fragment
    // since it only depends on uDistance, not world position. The minor
    // (faint) tier is always exactly one nice-sequence step finer than
    // major (a ~2-2.5x gap, never the old scheme's flat 10x jump).
    float n = niceIndexFor(uDistance / uZoomRatio);
    float majorSpacing = niceValue(n);
    float fineSpacing = niceValue(n - 1.0);

    // Fixed on-screen dot size (pixels), converted to world units at the
    // current zoom -- matches the old glPointSize(1.75)/glPointSize(2.5)
    // pixel-space sizing.
    float minorRadius = 1.75 * 0.5 * uWorldPerPixel;
    float majorRadius = 2.5 * 0.5 * uWorldPerPixel;

    float fineAlpha = dotAlpha(vWorld, fineSpacing, minorRadius) * uMinorColor.a;
    float majAlpha = dotAlpha(vWorld, majorSpacing, majorRadius) * uMajorColor.a;

    vec3 color = mix(uMinorColor.rgb, uMajorColor.rgb, step(0.001, majAlpha));
    float alpha = max(fineAlpha, majAlpha);

    if (alpha < 0.003) {
        discard;
    }

    FragColor = vec4(color, alpha);
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
