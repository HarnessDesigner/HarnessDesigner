# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from OpenGL import GL

from . import compiler as _compiler
from ... import check_types as _check_types


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;
layout(location = 1) in vec3 in_smoothNormalLocal;
layout(location = 2) in vec3 in_faceNormalLocal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;
uniform int normalMode;

// See gl.shaders.faces' identical uniforms -- WireStripe.render_segment
// (objects.objects_3d.wire) sets these on this program too (not just
// faces_program) so the shared stripe helix mesh's debug edge rendering
// windows to the same [stripeClipStart, stripeClipStop] segment instead
// of drawing the whole shared mesh with a naive, non-rebased transform.
uniform float stripeClipStop;
uniform float stripeClipStart;

out vec3 fragPositionWorld;
out vec3 fragNormalWorld;
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

    vec3 in_normalLocal = normalMode == 0 ? in_smoothNormalLocal : in_faceNormalLocal;
    vec3 scaledNormal = in_normalLocal / effectiveScale;
    vec3 worldNormal = rotationMatrix * scaledNormal;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragNormalWorld = normalize(worldNormal);
    fragLocalZ = in_vertexLocal.z;
}
"""

GEOMETRY_SHADER = """
#version 330 core

layout(triangles) in;
layout(line_strip, max_vertices = 6) out;  // 3 edges/normals × 2 vertices each

in vec3 fragPositionWorld[];
in vec3 fragNormalWorld[];
in float fragLocalZ[];

out float fragLocalZGeom;

uniform mat4 projection;
uniform mat4 view;
uniform int renderMode;      // 0 = edges, 1 = normals
uniform float normalLength;

void emitEdges() {
    // Emit three edges of the triangle as line segments
    for (int i = 0; i < 3; i++) {
        int next = (i + 1) % 3;

        gl_Position = gl_in[i].gl_Position;
        fragLocalZGeom = fragLocalZ[i];
        EmitVertex();

        gl_Position = gl_in[next].gl_Position;
        fragLocalZGeom = fragLocalZ[next];
        EmitVertex();

        EndPrimitive();
    }
}

void emitNormals() {
    for (int i = 0; i < 3; i++) {
        vec3 normalEnd = fragPositionWorld[i] + fragNormalWorld[i] * normalLength;

        gl_Position = gl_in[i].gl_Position;
        fragLocalZGeom = fragLocalZ[i];
        EmitVertex();

        gl_Position = projection * view * vec4(normalEnd, 1.0);
        fragLocalZGeom = fragLocalZ[i];
        EmitVertex();

        EndPrimitive();
    }
}

void main() {
    if (renderMode == 0) {
        emitEdges();
    } else {
        emitNormals();
    }
}
"""

FRAGMENT_SHADER = """
#version 330 core

in float fragLocalZGeom;

out vec4 FragColor;

uniform vec4 materialAmbient;
uniform vec4 materialDiffuse;
uniform vec4 materialSpecular;
uniform float materialShininess;
uniform vec4 materialEmissive;
uniform float stripeClipStop;
uniform float stripeClipStart;


void main() {
    // See gl.shaders.faces' identical discard for the full explanation.
    if (stripeClipStop > 0.0 &&
        (fragLocalZGeom > stripeClipStop || fragLocalZGeom < stripeClipStart)) {
        discard;
    }

    vec3 result = materialAmbient.rgb + materialDiffuse.rgb + materialSpecular.rgb + materialEmissive.rgb;
    float alpha = materialDiffuse.a;

    FragColor = vec4(result, alpha);
}
"""


@_check_types.do
def compile_program():
    """Compile and link the edges shader program."""
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
        raise RuntimeError(f"Edges program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(geometry_shader)
    GL.glDeleteShader(fragment_shader)

    return program
