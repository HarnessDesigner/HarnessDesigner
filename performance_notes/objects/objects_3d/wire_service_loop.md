# harness_designer/objects/objects_3d/wire_service_loop.py

## Line 286-287 (`_is_clear`) — neighbour mesh re-transformed on every roll-search step
For every candidate pose that passes the broad-phase OBB test, `_is_clear`
rebuilds each overlapping neighbour's full world-space mesh with
`_mesh_world_triangles(obj3d._vbo, ...)`. Those neighbours do not move while a
move/rotate session is running, yet their transformed triangles are recomputed
for every roll-search step. The session already caches per-candidate OBB
triangles (`_MoveSession`, built by `begin_move_session`, line 631), so the
mesh triangles belong in that same cache. Building them once per session and
indexing by owner would remove a transform of ~thousands of vertices per
neighbour per step.

## Line 136-187 (`_rays_vs_triangles_batched`) — (M, N, 3) intermediates
This is batched over both rays and triangles, which is the right idea for
small inputs, but every intermediate (`h`, `s`, `q`, the broadcast `ro`/`rd`)
is a full `(M, N, 3)` array. `_meshes_intersect` (line 191-214) calls it with
M = 3 × (edges of one mesh) and N = triangles of the other. A cylinder mesh
from `shapes/cylinder.py` is on the order of 1,400 triangles, so one call is
about 4,200 × 1,400 pairs — roughly 6 million pairs, each with several
3-component float64 arrays alive at once, on the order of 150 MB per
intermediate. That happens twice per `_meshes_intersect` (both directions) and
once per roll-search step that reaches the narrow phase.

Options, in order of payoff:
1. Skip the narrow phase when the OBB test already says clear (already done).
2. Chunk the ray axis (e.g. 256 rays at a time) to bound peak memory and keep
   intermediates in cache; cost is the same, peak memory drops by 1-2 orders
   of magnitude.
3. Use a bounding-volume pre-filter on the triangles (a per-triangle AABB test
   against the candidate's own AABB) before the full batched test.

## Line 749-761 (`_resolve_collision._roll_search`) — 16 roll steps per candidate, each running `_is_clear`
Each roll step builds a candidate OBB (`_candidate_obb`, cheap) and then calls
`_is_clear`, which does the narrow phase above only when the broad phase finds
an overlap. The 16-step sweep (`range(16)`) is sized for a whole turn; if most
steps fail the broad phase this is cheap, but for a crowded harness where every
step overlaps a neighbour, it is 16 narrow-phase calls per roll search. The
mesh-cache fix above would make each of those cheaper; the step count is a
behaviour choice and is not changed here.

## Line 608-641 (`begin_move_session`) — session setup
Runs once per interactive move, so it is not a per-frame cost. Its output is
the cache the two items above should extend.
