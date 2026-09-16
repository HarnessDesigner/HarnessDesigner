// ASCII characters only -- this file is read with encoding='ascii' (see
// faces.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;
layout(location = 1) in vec3 in_smoothNormalLocal;
layout(location = 2) in vec3 in_faceNormalLocal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;
uniform int normalMode;

// <= 0.0 means "not a stripe, no clipping". Only WireStripe.render_segment()
// (and objects_schematic/wire.py's own stripe tail) ever sets this to a
// nonzero value for its own draw; every other caller either leaves it
// untouched or explicitly resets it to 0.0 (see FacesProgram.stripe_clip_stop
// in gl/shaders/program.py), so it defaults to 0.0 for every other object
// without needing to be set on every draw call. When active, the mesh
// already has real-world units baked into local Z (see shapes/helix.py),
// so local Z scaling is skipped entirely instead of being stretched to the
// segment length like every other axis/object -- objectScale.z is unused
// for stripe geometry.
uniform float stripeClipStop;

// Only meaningful when stripeClipStop > 0.0 -- the other end of the
// window into the shared stripe helix mesh (see stripeClipStop above).
// Same contract as stripeClipStop.
uniform float stripeClipStart;

out vec3 fragPositionWorld;
out vec3 fragNormalWorld;
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
    vec3 effectiveScale = stripeClipStop > 0.0 ? vec3(objectScale.xy, 1.0) : objectScale;

    // Stripe geometry: X/Y (the radial helix pattern) stay driven by the
    // raw local vertex, which already encodes the correct phase at
    // whatever raw mesh Z it sits at -- baked into the mesh itself, see
    // shapes/helix.py. Z re-bases to this segment's own local origin
    // (subtracting stripeClipStart) so the surviving [start, stop]
    // window renders at this segment's actual position instead of
    // wherever its raw Z happens to be in the shared mesh.
    vec3 scaledVertex = stripeClipStop > 0.0
        ? vec3(in_vertexLocal.xy * objectScale.xy, in_vertexLocal.z - stripeClipStart)
        : in_vertexLocal * effectiveScale;

    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedVertex = rotationMatrix * scaledVertex;
    vec3 worldPosition = rotatedVertex + objectPosition;

    vec3 in_normalLocal = normalMode == 0 ? in_smoothNormalLocal : in_faceNormalLocal;
    vec3 scaledNormal = in_normalLocal / effectiveScale;
    vec3 worldNormal = rotationMatrix * scaledNormal;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragNormalWorld = normalize(worldNormal);
    fragLocalZ = in_vertexLocal.z;
}