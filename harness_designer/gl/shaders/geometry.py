from OpenGL import GL

from . import compiler as _compiler


SHADER = """
#version 330 core

layout(triangles) in;
layout(triangle_strip, max_vertices = 18) out;

in vec3 fragPositionWorld[];
in vec3 fragNormalWorld[];

out vec3 fragPositionGeom;
out vec3 fragNormalGeom;
out float isReflection;
out vec3 debugColor;

uniform mat4 projection;
uniform mat4 view;
uniform float floorY;
uniform int objectHasReflection;

// Debug rendering uniforms
uniform int showEdges;
uniform int showVertices;
uniform int showNormals;
uniform int showFaces;
uniform float normalLength;
uniform vec3 edgeColor;  // Configurable edge color from Python

void emitOriginalTriangle() {
    for(int i = 0; i < 3; i++) {
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPositionWorld[i];
        fragNormalGeom = fragNormalWorld[i];
        isReflection = 0.0;
        debugColor = vec3(-1.0);  // Signal: use normal material rendering
        EmitVertex();
    }
    EndPrimitive();
}

void emitReflectedTriangle() {
    // Emit in reverse order to maintain correct winding
    for(int i = 2; i >= 0; i--) {
        vec3 reflectedPos = fragPositionWorld[i];
        reflectedPos.y = 2.0 * floorY - reflectedPos.y;

        vec3 reflectedNormal = fragNormalWorld[i];
        reflectedNormal.y = -reflectedNormal.y;

        gl_Position = projection * view * vec4(reflectedPos, 1.0);
        fragPositionGeom = reflectedPos;
        fragNormalGeom = normalize(reflectedNormal);
        isReflection = 1.0;
        debugColor = vec3(-1.0);
        EmitVertex();
    }
    EndPrimitive();
}

void emitEdges() {
    // Emit three edges of the triangle as line segments
    for(int i = 0; i < 3; i++) {
        int nextVertex = (i + 1) % 3;

        // Start of edge
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPositionWorld[i];
        fragNormalGeom = fragNormalWorld[i];
        isReflection = 0.0;
        debugColor = edgeColor;  // Use configurable edge color
        EmitVertex();

        // End of edge
        gl_Position = gl_in[nextVertex].gl_Position;
        fragPositionGeom = fragPositionWorld[nextVertex];
        fragNormalGeom = fragNormalWorld[nextVertex];
        isReflection = 0.0;
        debugColor = edgeColor;
        EmitVertex();

        EndPrimitive();
    }
}

void emitVertices() {
    // Emit each vertex of the triangle as a point
    for(int i = 0; i < 3; i++) {
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPositionWorld[i];
        fragNormalGeom = fragNormalWorld[i];
        isReflection = 0.0;
        debugColor = vec3(1.0, 0.0, 0.0);  // Red vertices
        gl_PointSize = 6.0;
        EmitVertex();
        EndPrimitive();
    }
}

void emitNormals() {
    // Emit each normal as a line segment from vertex
    for(int i = 0; i < 3; i++) {
        vec3 normalEndWorld = fragPositionWorld[i] + fragNormalWorld[i] * normalLength;

        // Start of normal (at vertex position)
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPositionWorld[i];
        fragNormalGeom = fragNormalWorld[i];
        isReflection = 0.0;
        debugColor = vec3(1.0, 1.0, 1.0);  // White normals
        EmitVertex();

        // End of normal
        gl_Position = projection * view * vec4(normalEndWorld, 1.0);
        fragPositionGeom = normalEndWorld;
        fragNormalGeom = fragNormalWorld[i];
        isReflection = 0.0;
        debugColor = vec3(1.0, 1.0, 1.0);  // White normals
        EmitVertex();

        EndPrimitive();
    }
}

void main() {
    // Emit the original triangle only if faces are enabled
    if (showFaces == 1) {
        emitOriginalTriangle();

        // Emit reflection if enabled
        if (objectHasReflection == 1) {
            emitReflectedTriangle();
        }
    }

    // === DEBUG RENDERING ===

    if (showEdges == 1) {
        emitEdges();
    }

    if (showVertices == 1) {
        emitVertices();
    }

    if (showNormals == 1) {
        emitNormals();
    }
}
"""


def compile_shader():
    return _compiler.compile(SHADER, GL.GL_GEOMETRY_SHADER)