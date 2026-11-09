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

// <= 0.0 means "not a stripe, no clipping". Only objects_schematic/wire.py's
// own stripe tail ever sets this to a nonzero value for its own draw; every other caller either leaves it
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

// ---- Twisted conductors (TWISTED_WIRE_DESIGN.md sections 5 and 7) ----------------------------------------------------------
// twistBatch != 0 draws EVERY wire, cable and bundle of a frame in ONE call (gl/wire_batch.py); 0, the default, is every other
// draw (ordinary meshes), and gl/wire_batch.py puts it back to 0 after its draw, the same contract as stripeClipStop above.
//
// The draw is a list of twistEntryCount entries in the texture buffer twistEntries, one per conductor of a wire in view, 10 texels
// each:
//   0: the wire's first row in twistPieces and its row count (ints), the entry's first vertex in the draw (an int), the
//      stripe's half angle (0 = no stripe)
//   1: the twist rate and the conductor's circle (centre x, centre y, radius)
//   2, 3, 4: ambient, diffuse, specular     5: shininess and emissive (r, g, b)     6, 7, 8: the stripe's ambient/diffuse/specular
//   9: the vertex, within the wire's own draw, where the entry's rows begin (an int; 0 for an entry of the whole wire, more for the
//      bare end of a wire that crimps into a terminal, which is an entry of its own)
// A wire owns consecutive rows of the texture buffer twistPieces (gl/wire_pool.py), a row is 5 texels:
//   0: position.xyz (where the piece starts), length
//   1: rotation quaternion (w, x, y, z)
//   2: phase, ring count, first vertex of the piece in this wire's draw (an int stored with intBitsToFloat), unused
//   3: mitre at the start (the direction of the neighbouring piece in THIS piece's local frame, and the distance over which the
//      ring shift fades in; w <= 0 means no neighbour: cut square)
//   4: the same for the end
// There are NO attributes: the vertex comes from gl_VertexID. A vertex finds its entry by a binary search on the entries'
// first-vertex values, then its piece in the wire's rows by a second one (loadPiece), so a piece takes exactly the vertices it has
// (a tube of `rings` rings and TWIST_SIDES sides drawn as separate triangles, TWIST_SIDES * 6 vertices per ring-to-ring band) and
// a wire's rows can sit anywhere in the buffer and be moved. The entry's number goes on to the fragment shader, which reads the
// material from the same texels. Everything is in real mm in the piece's own frame (local +Z is the piece direction, objectScale
// is NOT used): ring k sits at z = length * k / (rings - 1) and the whole cross-section turns rigidly by phase + rate * z about the
// axis, so the conductor's centre follows a helix.
const int TWIST_SIDES = 16;
const float TWIST_PI = 3.14159265358979;

uniform int twistBatch;
uniform samplerBuffer twistPieces;
uniform samplerBuffer twistEntries;
uniform int twistEntryCount;

// what twistVertex and main work from: the batched wire's entry and piece
int pRings;
float pLength;
float pPhase;
vec4 pStart;
vec4 pEnd;
vec3 pPosition;
vec4 pRotation;
int pVertex;
float pRate;
vec3 pProfile;

out vec3 fragPositionWorld;
out vec3 fragNormalWorld;
out float fragLocalZ;

// The entry (see twistBatch) of the batched wire this vertex belongs to, -1 for everything else.
flat out int fragEntry;

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

// The normal of a ring vertex at a joint of two pieces, as a smooth bend has it: the radial normal n of this piece and the radial
// normal the NEIGHBOURING piece has at the same vertex (this piece's n turned by the minimal rotation that takes this piece's +Z
// to *neighbour*, the neighbour's direction in this piece's frame) are two directions 10 degrees or so apart, and the surface
// between them is smooth, so at the joint the normal is their bisector (which is also what the neighbour computes, so the two
// pieces agree). Rodrigues' form of that rotation: R n = n + v x n + v x (v x n) / (1 + c), v = z x d, c = z . d.
vec3 smoothAcrossJoint(vec3 n, vec3 neighbour) {
    vec3 v = vec3(-neighbour.y, neighbour.x, 0.0);
    vec3 rotated = n + cross(v, n) + cross(v, cross(v, n)) / (1.0 + neighbour.z);

    return normalize(n + rotated);
}

// The vertex gl_VertexID names, for a twisted conductor: its position and normal
// in the segment's local frame, and its z along the segment before any mitre
// shift (what fragLocalZ carries).
void twistVertex(out vec3 position, out vec3 normal, out float localZ, out float stripe) {
    int bandSize = TWIST_SIDES * 6;
    int band = pVertex / bandSize;
    int inBand = pVertex - band * bandSize;
    int side = inBand / 6;
    int corner = inBand - side * 6;

    // two triangles per quad, wound so that the outside is the counter-clockwise face:
    // (ring, side) (ring, side + 1) (ring + 1, side)   and   (ring + 1, side) (ring, side + 1) (ring + 1, side + 1)
    int ringStep = (corner == 2 || corner == 3 || corner == 5) ? 1 : 0;
    int sideStep = (corner == 1 || corner == 4 || corner == 5) ? 1 : 0;

    int ring = band + ringStep;
    int sideIndex = (side + sideStep) % TWIST_SIDES;

    float z = pLength * float(ring) / float(pRings - 1);
    float around = 2.0 * TWIST_PI * float(sideIndex) / float(TWIST_SIDES);
    float theta = pPhase + pRate * z;

    float cosT = cos(theta);
    float sinT = sin(theta);
    mat2 turn = mat2(cosT, sinT, -sinT, cosT);

    vec2 outward = vec2(cos(around), sin(around));
    vec2 p = turn * (pProfile.xy + pProfile.z * outward);

    // d(position)/d(around) and d(position)/d(z) of the sheared tube; their cross product is the outward normal
    vec3 alongAround = vec3(turn * (pProfile.z * vec2(-outward.y, outward.x)), 0.0);
    vec3 alongZ = vec3(pRate * vec2(-p.y, p.x), 1.0);
    normal = normalize(cross(alongAround, alongZ));

    // Across a bend the normal turns smoothly from this piece's to the joint's bisector over the same distance the mitre fades in
    // over (so the rounded corner, a run of short pieces, shades as one surface instead of as the facets it is cut into).
    if (pEnd.w > 0.0 && pEnd.z > -0.99) {
        float f = clamp((z - (pLength - pEnd.w)) / pEnd.w, 0.0, 1.0);
        normal = normalize(mix(normal, smoothAcrossJoint(normal, pEnd.xyz), f));
    }

    if (pStart.w > 0.0 && pStart.z > -0.99) {
        float f = clamp(1.0 - z / pStart.w, 0.0, 1.0);
        normal = normalize(mix(normal, smoothAcrossJoint(normal, pStart.xyz), f));
    }

    // The mitre: both rings of a bend are moved along their own axis onto the plane that bisects the bend,
    // t = -(p . d_other) / (1 + d . d_other), faded in over the last (first) twistEnd.w (twistStart.w) mm.
    float shift = 0.0;

    if (pEnd.w > 0.0) {
        float t = -dot(pEnd.xy, p) / (1.0 + pEnd.z);
        shift += t * clamp((z - (pLength - pEnd.w)) / pEnd.w, 0.0, 1.0);
    }

    if (pStart.w > 0.0) {
        float t = -dot(pStart.xy, p) / (1.0 + pStart.z);
        shift += t * clamp(1.0 - z / pStart.w, 0.0, 1.0);
    }

    position = vec3(p, z + shift);
    localZ = z;

    // The stripe runs along the side of the conductor that faces away from the cable's axis, snapped to a side
    // so that its centre is exactly on a vertex (the distance is then exact across every quad, not interpolated
    // through the stripe's own centre).
    float sideAngle = 2.0 * TWIST_PI / float(TWIST_SIDES);
    // (the centre conductor of a six or more conductor cable sits on the axis, where atan is undefined: take +X)
    float profileAngle = 0.0;

    if (dot(pProfile.xy, pProfile.xy) > 1e-8) {
        profileAngle = atan(pProfile.y, pProfile.x);
    }

    float centre = round(profileAngle / sideAngle) * sideAngle;
    float aroundEnd = sideAngle * float(side + sideStep);
    stripe = abs(mod(aroundEnd - centre + TWIST_PI, 2.0 * TWIST_PI) - TWIST_PI);
}

// The piece of the wire whose rows are the count rows from row base that vertex (counted from the start of the wire's draw)
// belongs to: everything twistVertex works from except the rate and the profile.
void loadPiece(int base, int count, int vertex) {
    int lo = 0;
    int hi = count - 1;

    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;

        if (floatBitsToInt(texelFetch(twistPieces, (base + mid) * 5 + 2).z) <= vertex) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }

    int row = (base + lo) * 5;
    vec4 head = texelFetch(twistPieces, row);
    vec4 turn = texelFetch(twistPieces, row + 1);
    vec4 ring = texelFetch(twistPieces, row + 2);

    pPosition = head.xyz;
    pLength = head.w;
    pRotation = turn;
    pPhase = ring.x;
    pRings = int(ring.y + 0.5);
    pStart = texelFetch(twistPieces, row + 3);
    pEnd = texelFetch(twistPieces, row + 4);
    pVertex = vertex - floatBitsToInt(ring.z);
}

// The entry gl_VertexID belongs to (see twistBatch above), and then its piece.
void loadBatchPiece() {
    int lo = 0;
    int hi = twistEntryCount - 1;

    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;

        if (floatBitsToInt(texelFetch(twistEntries, mid * 10).z) <= gl_VertexID) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }

    vec4 head = texelFetch(twistEntries, lo * 10);
    vec4 shape = texelFetch(twistEntries, lo * 10 + 1);
    int offset = floatBitsToInt(texelFetch(twistEntries, lo * 10 + 9).x);

    fragEntry = lo;
    pRate = shape.x;
    pProfile = shape.yzw;

    loadPiece(floatBitsToInt(head.x), floatBitsToInt(head.y), gl_VertexID - floatBitsToInt(head.z) + offset);
}

void main() {
    fragEntry = -1;

    if (twistBatch != 0) {
        loadBatchPiece();

        vec3 twistPosition;
        vec3 twistNormal;
        float twistZ;
        float twistStripe;
        twistVertex(twistPosition, twistNormal, twistZ, twistStripe);

        mat3 twistRotation = quaternionToMatrix(pRotation);
        vec3 twistWorld = twistRotation * twistPosition + pPosition;

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