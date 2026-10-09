# harness_designer/objects/objects_3d/wire.py

## Line 500-596 (`Wire.render`) — per-segment shader program churn and uniform resets
Each sub-segment costs three `with program:` context entries (faces, edges,
vertices), each followed by two uniform writes (`stripe_clip_start`,
`stripe_clip_stop`), then a full `super().render()` (which re-binds the same
programs again internally), then the stripe draw. For a wire with N segments
that is roughly 9N program binds and 6N uniform uploads per frame before any
geometry is drawn. The clip reset is unconditional on purpose (see the comment
at line 552-573), so the fix is not to delete it but to batch it: bind each of
the three programs once around the whole segment loop and reset the clip
uniforms only when the previous draw actually set them (track a dirty flag set
by `WireStripe.render_segment`). Typical wires have only a few segments, so
this is not a problem on its own; it multiplies with the number of wires in the
scene, which is the case to watch for.

## Line 351-369 (`Wire._segment_transforms`) — rebuilt on every call
`_segment_transforms` is a generator that allocates a `Point` and an `Angle`
per segment and recomputes `_rotation_from_direction` for each. It is called
from four places per frame or per move: `render` (line 535), `_segment_world_corners`
(line 438, reached from both `_compute_obb` and `_compute_aabb`), and
`hit_test_step3` (line 470). Nothing it depends on changes between those calls
unless a waypoint moved, so the transforms could be cached and invalidated
from `_bind_waypoints`/`_update_position`/`_update_angle`/`_update_scale`
(the same invalidation points that already call `_recalculate_geometry`).

## Line 300-337 (`Wire._recalculate_geometry`) — three walks of the segment list per drag move
Every endpoint or waypoint move calls this synchronously (`_update_position`,
line 340). Inside it:
- `self._segments()` is walked once for the length (lines 310-314),
- `_compute_obb` (line 336) calls `_segment_world_corners`, which walks
  `_segment_transforms()` again (line 438),
- `_compute_aabb` (line 337) calls `_segment_world_corners` a second time,
  rebuilding the same corner array from scratch.

So an endpoint drag does three segment walks and two identical corner
builds per mouse-move event. Computing the corners once and feeding both the
OBB and the AABB would halve the corner work. Caching the segment transforms
(above) would remove the rest.

## Line 459-479 (`Wire.hit_test_step3`) — full mesh transform per segment
For each sub-segment this transforms the entire cylinder mesh
(`vertices_local * seg_scale @ seg_angle`, line 473), which is O(V) per segment
per candidate wire on every hover/click that reaches this test. The picker
already avoids this for whole objects by transforming the ray into local space
once (`BaseVar`/`gl.object_picker`). The same approach works per segment: one
inverse transform of the ray origin and direction per segment, then test
against the untransformed local triangles. That turns the per-segment cost
from O(V) into O(1) plus the (unavoidable) triangle test.

## Line 233-262 (`Wire.is_housing_attached`) — full project scan, and dead code
Scans every cavity and every terminal in the project per call. No callers
exist under `harness_designer/` (checked with `dep_trace.py --calls`), so it
currently costs nothing. If it is ever wired into a drag-start check, it should
use a per-housing index rather than a linear scan on each drag. Flagged as
possibly dead code; not removed.

## Line 1219-1222 and 1244-1245 (`WireStripe.__init__`) — capacity walk at construction
Walks the wire's full segment list once to compute `required`, then calls
`_ensure_stripe_capacity`. That is one-time per wire construction and is fine.
The `_ensure_stripe_capacity` fast path (line 1271) is a plain attribute compare
with no GL call, which is the right shape.

## Line 1249-1273 (`WireStripe._ensure_stripe_capacity`) — reads the DB row on every recalc
`_recalculate_geometry` calls this whenever the wire has a stripe (line 323),
so every drag move reads `project.db_obj.wire_stripe_max_length`. The value is a
single scalar read, so this is cheap, but it is a DB-backed attribute read on
the hot drag path. If that attribute is backed by a row lookup rather than a
plain field, caching the last-seen max on the stripe would avoid it.
