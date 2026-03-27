from OpenGL import GL

from . import compiler as _compiler


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;
layout(location = 1) in vec3 in_normalLocal;

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

    return mat3(
        1.0 - 2.0 * (yy + zz), 2.0 * (xy + wz), 2.0 * (xz - wy),
        2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz + wx),
        2.0 * (xz + wy), 2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy)
    );
}

void main() {
    vec3 scaledVertex = in_vertexLocal * objectScale;
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedVertex = rotationMatrix * scaledVertex;
    vec3 worldPosition = rotatedVertex + objectPosition;

    vec3 scaledNormal = in_normalLocal / objectScale;
    vec3 worldNormal = rotationMatrix * scaledNormal;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragNormalWorld = normalize(worldNormal);
}
"""

GEOMETRY_SHADER = """
#version 330 core

layout(triangles) in;
layout(line_strip, max_vertices = 6) out;  // 3 edges/normals × 2 vertices each

in vec3 fragPositionWorld[];
in vec3 fragNormalWorld[];

out vec3 lineColor;

uniform mat4 projection;
uniform mat4 view;
uniform int renderMode;      // 0 = edges, 1 = normals
uniform float normalLength;
uniform vec3 edgeColor;

void emitEdges() {
    // Emit three edges of the triangle as line segments
    for (int i = 0; i < 3; i++) {
        int next = (i + 1) % 3;

        lineColor = edgeColor;
        gl_Position = gl_in[i].gl_Position;
        EmitVertex();

        lineColor = edgeColor;
        gl_Position = gl_in[next].gl_Position;
        EmitVertex();

        EndPrimitive();
    }
}

void emitNormals() {
    for (int i = 0; i < 3; i++) {
        vec3 normalEnd = fragPositionWorld[i] + fragNormalWorld[i] * normalLength;

        lineColor = vec3(1.0, 1.0, 1.0);
        gl_Position = gl_in[i].gl_Position;
        EmitVertex();

        lineColor = vec3(1.0, 1.0, 1.0);
        gl_Position = projection * view * vec4(normalEnd, 1.0);
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

in vec3 lineColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(lineColor, 1.0);
}
"""


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
