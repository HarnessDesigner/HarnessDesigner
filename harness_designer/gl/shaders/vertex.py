from OpenGL import GL

from . import compiler as _compiler


# Vertex Shader - applies position and rotation per instance
SHADER = """
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;   // Local/model-space vertex coordinate
layout(location = 1) in vec3 in_normalLocal;   // Local/model-space normal

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;

out vec3 fragPositionWorld;
out vec3 fragNormalWorld;

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

    // Construct as column-major (transpose of your current matrix)
    return mat3(
        1.0 - 2.0 * (yy + zz), 2.0 * (xy + wz), 2.0 * (xz - wy),
        2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz + wx),
        2.0 * (xz + wy), 2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy)
    );
}

void main() {
    // Transform local vertex to world space: Scale → Rotate → Translate (SRT)
    vec3 scaledVertex = in_vertexLocal * objectScale;
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedVertex = rotationMatrix * scaledVertex;
    vec3 worldPosition = rotatedVertex + objectPosition;

    // Transform normal to world space: Inverse-scale → Rotate (no translation)
    vec3 scaledNormal = in_normalLocal / objectScale;  // Inverse scale for normals
    vec3 worldNormal = rotationMatrix * scaledNormal;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragNormalWorld = normalize(worldNormal);
}
"""


def compile_shader():
    return _compiler.compile(SHADER, GL.GL_VERTEX_SHADER)


