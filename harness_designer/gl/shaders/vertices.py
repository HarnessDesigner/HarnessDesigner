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

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
}
"""

GEOMETRY_SHADER = """
#version 330 core

layout(triangles) in;
layout(points, max_vertices = 3) out;

in vec3 fragPositionWorld[];

out vec3 pointColor;

uniform vec3 vertexColor;

void main() {
    for (int i = 0; i < 3; i++) {
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