// ASCII characters only -- this file is read with encoding='ascii' (see
// faces.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

layout(triangles) in;

// 3 for original triangle + 3 for reflection
layout(triangle_strip, max_vertices = 6) out;

in vec3 fragPositionWorld[];
in vec3 fragNormalWorld[];
in float fragLocalZ[];

out vec3 fragPositionGeom;
out vec3 fragNormalGeom;
out float isReflection;
out float fragLocalZGeom;

uniform mat4 projection;
uniform mat4 view;
uniform float floorY;
uniform int objectHasReflection;

void main() {
    // Emit the original triangle
    for (int i = 0; i < 3; i++) {
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPositionWorld[i];
        fragNormalGeom = fragNormalWorld[i];
        fragLocalZGeom = fragLocalZ[i];
        isReflection = 0.0;
        EmitVertex();
    }
    EndPrimitive();

    // Emit reflection if enabled
    if (objectHasReflection == 1) {
        for (int i = 2; i >= 0; i--) {
            vec3 reflectedPos = fragPositionWorld[i];
            reflectedPos.y = 2.0 * floorY - reflectedPos.y;

            vec3 reflectedNormal = fragNormalWorld[i];
            reflectedNormal.y = -reflectedNormal.y;

            gl_Position = projection * view * vec4(reflectedPos, 1.0);
            fragPositionGeom = reflectedPos;
            fragNormalGeom = normalize(reflectedNormal);
            fragLocalZGeom = fragLocalZ[i];
            isReflection = 1.0;
            EmitVertex();
        }
        EndPrimitive();
    }
}