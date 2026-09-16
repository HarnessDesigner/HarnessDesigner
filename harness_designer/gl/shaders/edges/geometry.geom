// ASCII characters only -- this file is read with encoding='ascii' (see
// edges.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

layout(triangles) in;

// 3 edges/normals x 2 vertices each
layout(line_strip, max_vertices = 6) out;

in vec3 fragPositionWorld[];
in vec3 fragNormalWorld[];
in float fragLocalZ[];

out float fragLocalZGeom;

uniform mat4 projection;
uniform mat4 view;

// 0 = edges, 1 = normals
uniform int renderMode;

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