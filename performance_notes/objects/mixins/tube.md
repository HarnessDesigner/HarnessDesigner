# harness_designer/objects/mixins/tube.py

How every wire, cable and bundle is drawn, in 3D and on the board (`TubeMixin`). The per-frame path is already cached: the cost per wire per frame is visibility, two `mark_visible` writes, a cache check and one `BATCH.add` per conductor. The cost that matters is the rebuild, which runs whenever a wire's path changes, so on every frame of a drag that moves it.

## Line 342-374 (`_render_tubes`), 386-430 (`_batch_wire`) — per frame, cheap
`_twist_segments()` returns the cached plan unless the look or the path changed; `_batch_wire` rebuilds its entries only when the pool stamp, look, selection, material or bare-end state differ (five comparisons) and then calls `BATCH.add` once per conductor. Nothing to change.

## Line 239-292 (`_twist_segments`) — the rebuild builds a Python plan nobody draws with
When the path changes it calls `_segment_transforms()`, packs the segments into NumPy arrays (a Python loop over segments, `as_matrix_numpy` and `as_quat_numpy` per segment), runs `twisted_path.build_path` (compiled), then converts seven result arrays with `.tolist()` and builds one `TwistSegment` (a tuple, a list, a matrix, a `SegmentTwist` with two tuples) per piece in a Python loop (lines 270-282). The viewport draw uses only `_pool_rows` (the packed float32 rows written to the pool at line 288); the `TwistSegment` plan is used by `_curve_chords` (the floor outline and waypoint handles, only for a selected object), `ray_trace_meshes` and `Cable._lead_frames`.
Two costs follow:
- Speed: the seven `.tolist()` calls and the per-piece object loop run on every rebuild, so on every drag frame for every wire that moves, whether or not anything will ever read the plan. For a wire of a few hundred pieces that is a millisecond or more in the interpreter.
- Memory: the plan is kept on the object (`_twist_plan`) for its lifetime. A piece costs about 0.9 KB (measured on a representative `TwistSegment`: the position tuple, the quaternion list, the matrix view and the `SegmentTwist` with its two tuples, with their float objects), so 1,000 wires of 100 pieces is on the order of 90 MB held for data that is mostly never read. This is memory used when it does not need to be.
Fix: build the `TwistSegment` list lazily, only when `_curve_chords` / `ray_trace_meshes` / `_lead_frames` ask for it, and keep the NumPy arrays (`positions`, `piece_quats`, ... which are already computed) as the cached form. The viewport path then does the `build_path` call and `pack` and nothing else. Selected objects pay the plan build once per path change, which is what they need.

## Line 307-339 (`_render_floor_outline`) — see `gl/floor_outline.md`
Recomputes the silhouette every frame while the object is selected.

## Line 206-236 (`_conductor_materials`, `_segment_joins`)
Loops over conductors and segments once per rebuild. Fine.

## Memory
`_batch_entries` holds one 40-float array per conductor (160 bytes); `_pool_rows` is 80 bytes per piece (these are the data the GPU needs and are worth keeping).
