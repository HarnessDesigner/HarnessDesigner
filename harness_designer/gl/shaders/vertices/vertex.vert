// ASCII characters only -- this file is read with encoding='ascii' (see
// vertices.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;

// See gl.shaders.faces' identical uniforms -- WireStripe.render_segment
// (objects.objects_3d.wire) sets these on this program too (not just
// faces_program) so the shared stripe helix mesh's debug vertex
// rendering windows to the same [stripeClipStart, stripeClipStop]
// segment instead of drawing the whole shared mesh with a naive,
// non-rebased transform.
uniform float stripeClipStop;
uniform float stripeClipStart;

out vec3 fragPositionWorld;
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

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragLocalZ = in_vertexLocal.z;
}