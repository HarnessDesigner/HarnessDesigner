from OpenGL import GL

from . import compiler as _compiler


# Vertex Shader - applies position and rotation per instance
SHADER = """
#version 330 core

layout(location = 0) in vec3 in_position;
layout(location = 1) in vec3 in_normal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;

out vec3 fragPosition;
out vec3 fragNormal;

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
    vec3 scaledPosition = in_position;
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedPosition = rotationMatrix * scaledPosition;
    vec3 worldPosition = rotatedPosition + objectPosition;

    vec3 scaledNormal = in_normal / objectScale;
    vec3 rotatedNormal = rotationMatrix * scaledNormal;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPosition = worldPosition;
    fragNormal = normalize(rotatedNormal);
}
"""


def compile_shader():
    return _compiler.compile(SHADER, GL.GL_VERTEX_SHADER)


