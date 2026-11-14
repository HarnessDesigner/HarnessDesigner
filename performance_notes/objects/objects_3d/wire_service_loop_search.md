# harness_designer/objects/objects_3d/wire_service_loop_search.pyx

Cython search for a collision-free pose of a wire service loop (`LoopSearch`), built once per move session by `WireServiceLoop.begin_move_session`. Compiled with `boundscheck=False`, `wraparound=False`, `cdivision=True`, `nonecheck=False`; the inner functions are `nogil` and work on raw doubles (`_quat_mul`, `_quat_to_matrix`, `_compose`, `_clip`), with no Python objects, no `Angle` and no NumPy in the search.

## What it replaced (from the module docstring)
A pose cost about 610 us in NumPy (`Angle.from_quat` alone about 240 us, `points @ angle` about 55 us), so a slide of about 30 steps took about 0.5 s per mouse move and a placement where nothing clears took about 8 s; before that, mesh-against-mesh tests cost about 6 s each. The compiled search does a quaternion product, a 3x3 matrix and a handful of float compares per pose. That is the same lesson as `geometry/decimal.md`: the interpreted `Angle` machinery is two orders of magnitude slower than float arithmetic on four numbers.

## Cost now
Stage 1 (oriented-box separating-axis tests) is O(candidate boxes) per pose; stage 2 (mesh) only for boxes that overlap. Both are C loops. A 10-cell grid (`_GRID`) accelerates stage 2. `search` answers every `_resolve_collision` of the session without building Python objects. Remaining per-call overhead is the Python-to-Cython argument conversion at the call boundary; negligible next to the search.

## Memory
The `LoopSearch` is built per move session from everything the loop can hit (boxes and mesh vertices as C arrays) and freed with the session; it does not persist.
