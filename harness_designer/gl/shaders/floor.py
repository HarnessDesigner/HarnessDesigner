from OpenGL import GL

from . import compiler as _compiler


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_position;

uniform mat4 projection;
uniform mat4 view;

out vec3 fragWorldPos;

void main() {
    fragWorldPos = in_position;
    gl_Position = projection * view * vec4(in_position, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330 core

in vec3 fragWorldPos;

uniform float u_grid_step;
uniform vec4 u_primary_color;
uniform vec4 u_secondary_color;
uniform int u_grid_enable;

out vec4 FragColor;

// Anti-aliased line presence: 1.0 at the grid line centre, 0.0 away from it.
// linePixels controls the rendered width in screen pixels.
float lineMask(float coord, float gridStep, float linePixels) {
    float d = mod(coord, gridStep);
    d = min(d, gridStep - d);
    float fw = fwidth(coord);
    float hw = linePixels * fw;
    return 1.0 - smoothstep(hw - fw, hw + fw, d);
}

// Dot-on pattern: 1.0 when the dot is visible, 0.0 in the gap.
// Dots and gaps each occupy half of period (in world units).
float dotOn(float coord, float period) {
    return 1.0 - step(period * 0.5, mod(coord, period));
}

void main() {
    float x = fragWorldPos.x;
    float z = fragWorldPos.z;

    // --- Checkerboard tiles ---
    int tx = int(floor(x / u_grid_step));
    int tz = int(floor(z / u_grid_step));
    vec4 tileColor = (((tx + tz) & 1) == 0) ? u_primary_color : u_secondary_color;
    vec4 finalColor = tileColor;

    if (u_grid_enable != 0) {
        float minor_step = u_grid_step / 5.0;
        float dot_period = minor_step * 2.0;

        // Major grid lines (solid, ~2 pixels wide)
        float majorX = lineMask(x, u_grid_step, 1.5);
        float majorZ = lineMask(z, u_grid_step, 1.5);
        float majorGrid = clamp(majorX + majorZ, 0.0, 1.0);

        // Minor grid lines, excluding positions already covered by major lines
        float minorX = lineMask(x, minor_step, 0.8) * (1.0 - majorX);
        float minorZ = lineMask(z, minor_step, 0.8) * (1.0 - majorZ);

        // Dotted/stippled effect on minor lines:
        //   lines at x = n (parallel to Z axis) -> dot pattern sampled along Z
        //   lines at z = n (parallel to X axis) -> dot pattern sampled along X
        float dottedX = minorX * dotOn(z, dot_period);
        float dottedZ = minorZ * dotOn(x, dot_period);
        float minorGrid = clamp(dottedX + dottedZ, 0.0, 1.0);

        vec4 majorColor = vec4(0.65, 0.65, 0.65, 1.0);
        vec4 minorColor = vec4(0.35, 0.35, 0.35, 1.0);

        finalColor = mix(finalColor, minorColor, minorGrid);
        finalColor = mix(finalColor, majorColor, majorGrid);
    }

    FragColor = finalColor;
}
"""


def compile_program():
    """Compile and link the procedural floor/grid shader program."""
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
