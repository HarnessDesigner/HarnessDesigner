// (c) 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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

// ---- Twisted conductor (TWISTED_WIRE_DESIGN.md sections 5 and 7) ----------
// twistRings <= 0 (the default) means "not a twisted conductor": the vertex
// comes from the mesh attributes as always. Only Wire.render() (through
// shapes/twisted_tube.py) sets it, for the duration of one draw, and puts it
// back to 0; every other caller relies on it already being 0, the same contract
// as stripeClipStop above.
//
// When it is > 0 there are NO attributes: the vertex comes from gl_VertexID, a
// tube of twistRings rings and TWIST_SIDES sides drawn as separate triangles
// (TWIST_SIDES * 6 vertices per ring-to-ring band). Everything is in real mm in
// the segment's own frame (local +Z is the segment direction, objectScale is NOT
// used): ring k sits at z = twistLength * k / (twistRings - 1) and the whole
// cross-section turns rigidly by twistPhase + twistRate * z about the axis, so
// the conductor's centre follows a helix.
const int TWIST_SIDES = 16;
const float TWIST_PI = 3.14159265358979;

uniform int twistRings;

// segment length, mm
uniform float twistLength;

// radians per mm along the segment
uniform float twistRate;

// rotation of the cross-section at local z = 0, radians
uniform float twistPhase;

// the conductor's circle at z = 0 before the twist: centre x, centre y, radius (mm)
uniform vec3 twistProfile;

// The mitre at a bend. xyz = the direction of the neighbouring segment in THIS
// segment's local frame (previous one for twistStart, next one for twistEnd), w =
// the distance over which the ring shift fades in. w <= 0 means no neighbour: the
// end is cut square.
uniform vec4 twistStart;
uniform vec4 twistEnd;

out vec3 fragPositionWorld;
out vec3 fragNormalWorld;
out float fragLocalZ;

// Angular distance (radians) from the centre of a twisted conductor's stripe; the
// fragment shader paints the stripe where it is below twistStripeHalf. Far away
// (1000.0) for everything that is not a twisted conductor, so it never matches.
out float fragStripe;

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

// The vertex gl_VertexID names, for a twisted conductor: its position and normal
// in the segment's local frame, and its z along the segment before any mitre
// shift (what fragLocalZ carries).
void twistVertex(out vec3 position, out vec3 normal, out float localZ, out float stripe) {
    int bandSize = TWIST_SIDES * 6;
    int band = gl_VertexID / bandSize;
    int inBand = gl_VertexID - band * bandSize;
    int side = inBand / 6;
    int corner = inBand - side * 6;

    // two triangles per quad, wound so that the outside is the counter-clockwise face:
    // (ring, side) (ring, side + 1) (ring + 1, side)   and   (ring + 1, side) (ring, side + 1) (ring + 1, side + 1)
    int ringStep = (corner == 2 || corner == 3 || corner == 5) ? 1 : 0;
    int sideStep = (corner == 1 || corner == 4 || corner == 5) ? 1 : 0;

    int ring = band + ringStep;
    int sideIndex = (side + sideStep) % TWIST_SIDES;

    float z = twistLength * float(ring) / float(twistRings - 1);
    float around = 2.0 * TWIST_PI * float(sideIndex) / float(TWIST_SIDES);
    float theta = twistPhase + twistRate * z;

    float cosT = cos(theta);
    float sinT = sin(theta);
    mat2 turn = mat2(cosT, sinT, -sinT, cosT);

    vec2 outward = vec2(cos(around), sin(around));
    vec2 p = turn * (twistProfile.xy + twistProfile.z * outward);

    // d(position)/d(around) and d(position)/d(z) of the sheared tube; their cross product is the outward normal
    vec3 alongAround = vec3(turn * (twistProfile.z * vec2(-outward.y, outward.x)), 0.0);
    vec3 alongZ = vec3(twistRate * vec2(-p.y, p.x), 1.0);
    normal = normalize(cross(alongAround, alongZ));

    // The mitre: both rings of a bend are moved along their own axis onto the plane that bisects the bend,
    // t = -(p . d_other) / (1 + d . d_other), faded in over the last (first) twistEnd.w (twistStart.w) mm.
    float shift = 0.0;

    if (twistEnd.w > 0.0) {
        float t = -dot(twistEnd.xy, p) / (1.0 + twistEnd.z);
        shift += t * clamp((z - (twistLength - twistEnd.w)) / twistEnd.w, 0.0, 1.0);
    }

    if (twistStart.w > 0.0) {
        float t = -dot(twistStart.xy, p) / (1.0 + twistStart.z);
        shift += t * clamp(1.0 - z / twistStart.w, 0.0, 1.0);
    }

    position = vec3(p, z + shift);
    localZ = z;

    // The stripe runs along the side of the conductor that faces away from the cable's axis, snapped to a side
    // so that its centre is exactly on a vertex (the distance is then exact across every quad, not interpolated
    // through the stripe's own centre).
    float sideAngle = 2.0 * TWIST_PI / float(TWIST_SIDES);
    // (the centre conductor of a six or more conductor cable sits on the axis, where atan is undefined: take +X)
    float profileAngle = 0.0;

    if (dot(twistProfile.xy, twistProfile.xy) > 1e-8) {
        profileAngle = atan(twistProfile.y, twistProfile.x);
    }

    float centre = round(profileAngle / sideAngle) * sideAngle;
    float aroundEnd = sideAngle * float(side + sideStep);
    stripe = abs(mod(aroundEnd - centre + TWIST_PI, 2.0 * TWIST_PI) - TWIST_PI);
}

void main() {
    if (twistRings > 0) {
        vec3 twistPosition;
        vec3 twistNormal;
        float twistZ;
        float twistStripe;
        twistVertex(twistPosition, twistNormal, twistZ, twistStripe);

        mat3 twistRotation = quaternionToMatrix(objectRotation);
        vec3 twistWorld = twistRotation * twistPosition + objectPosition;

        gl_Position = projection * view * vec4(twistWorld, 1.0);
        fragPositionWorld = twistWorld;
        fragNormalWorld = normalize(twistRotation * twistNormal);
        fragLocalZ = twistZ;
        fragStripe = twistStripe;
        return;
    }

    fragStripe = 1000.0;

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