# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from OpenGL import GL

from . import compiler as _compiler
from ... import check_types as _check_types


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;

// See gl.shaders.faces' identical uniforms -- WireStripe.render_segment
// (objects.objects3d.wire) sets these on this program too (not just
// faces_program) so the shared stripe helix mesh's debug vertex
// rendering windows to the same [stripeClipStart, stripeClipStop]
// segment instead of drawing the whole shared mesh with a naive,
// non-rebased transform.
uniform float stripeClipStop;
uniform float stripeClipStart;

out vec3 fragPositionWorld;
out float fragLocalZ;

mat3 quaternionToMatrix(vec4 q) {
    float w = q.x;
    float x = q.y;
    float y = q.z;
    float z = q.w;

    float xx = x * x;
    float yy = y * y;
    float zz = z * z;
    float xy = x * y;
    float xz = x * z;
    float yz = y * z;
    float wx = w * x;
    float wy = w * y;
    float wz = w * z;

    return mat3(
        1.0 - 2.0 * (yy + zz), 2.0 * (xy + wz), 2.0 * (xz - wy),
        2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz + wx),
        2.0 * (xz + wy), 2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy)
    );
}

void main() {
    // See gl.shaders.faces' identical vertex shader for the full
    // explanation -- same stripe-geometry special case duplicated here.
    vec3 effectiveScale = stripeClipStop > 0.0 ? vec3(objectScale.xy, 1.0) : objectScale;

    vec3 scaledVertex = stripeClipStop > 0.0
        ? vec3(in_vertexLocal.xy * objectScale.xy, in_vertexLocal.z - stripeClipStart)
        : in_vertexLocal * effectiveScale;
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedVertex = rotationMatrix * scaledVertex;
    vec3 worldPosition = rotatedVertex + objectPosition;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragLocalZ = in_vertexLocal.z;
}
"""

GEOMETRY_SHADER = """
#version 330 core

layout(triangles) in;
layout(points, max_vertices = 3) out;

in vec3 fragPositionWorld[];
in float fragLocalZ[];

out vec3 pointColor;

uniform vec3 vertexColor;
uniform float stripeClipStop;
uniform float stripeClipStart;

void main() {
    for (int i = 0; i < 3; i++) {
        // Points have no fragment-level interpolation to discard against
        // (unlike faces/edges), so this culls the vertex outright instead
        // -- skip emitting it at all when it falls outside the stripe's
        // own visible window. See gl.shaders.faces for the full
        // explanation of stripeClipStart/stripeClipStop.
        if (stripeClipStop > 0.0 &&
            (fragLocalZ[i] > stripeClipStop || fragLocalZ[i] < stripeClipStart)) {
            continue;
        }

        pointColor = vertexColor;
        gl_Position = gl_in[i].gl_Position;
        gl_PointSize = 6.0;
        EmitVertex();
        EndPrimitive();
    }
}
"""

FRAGMENT_SHADER = """
#version 330 core

in vec3 pointColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(pointColor, 1.0);
}
"""


@_check_types.do
def compile_program():
    """Compile and link the vertices shader program."""
    vertex_shader = _compiler.compile(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
    geometry_shader = _compiler.compile(GEOMETRY_SHADER, GL.GL_GEOMETRY_SHADER)
    fragment_shader = _compiler.compile(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, geometry_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Vertices program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(geometry_shader)
    GL.glDeleteShader(fragment_shader)

    return program
