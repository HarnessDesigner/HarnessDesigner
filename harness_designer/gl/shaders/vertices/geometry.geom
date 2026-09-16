// ASCII characters only -- this file is read with encoding='ascii' (see
// vertices.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
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