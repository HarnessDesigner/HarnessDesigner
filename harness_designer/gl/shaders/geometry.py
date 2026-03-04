from OpenGL import GL

from . import compiler as _compiler


SHADER = """
#version 330 core

layout(triangles) in;
layout(triangle_strip, max_vertices = 6) out;

in vec3 fragPosition[];
in vec3 fragNormal[];

out vec3 fragPositionGeom;
out vec3 fragNormalGeom;
out float isReflection;

uniform mat4 projection;
uniform mat4 view;
uniform float floorY;
uniform int objectHasReflection;

void main() {
    // Emit original triangle
    for(int i = 0; i < 3; i++) {
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPosition[i];
        fragNormalGeom = fragNormal[i];
        isReflection = 0.0;
        EmitVertex();
    }
    EndPrimitive();

    // Emit reflection if enabled
    if (objectHasReflection == 1) {
        for(int i = 2; i >= 0; i--) {
            vec3 reflectedPos = fragPosition[i];
            reflectedPos.y = 2.0 * floorY - reflectedPos.y;

            vec3 reflectedNormal = fragNormal[i];
            reflectedNormal.y = -reflectedNormal.y;

            gl_Position = projection * view * vec4(reflectedPos, 1.0);

            fragPositionGeom = reflectedPos;
            fragNormalGeom = normalize(reflectedNormal);
            isReflection = 1.0;
            EmitVertex();
        }
        EndPrimitive();
    }
}
"""

def compile_shader():
    return _compiler.compile(SHADER, GL.GL_GEOMETRY_SHADER)
