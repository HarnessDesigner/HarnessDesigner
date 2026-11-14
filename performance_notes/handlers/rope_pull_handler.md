# harness_designer/handlers/rope_pull_handler.py

The solver behind every peg-board drag (housing, bundle, cable, wire service loop). `resolve_rigid_move` runs once per mouse move; the cost per move is the number of `_evaluate_points` runs times what one run costs. Rewritten 2026-11-13: the repeated-rebuild problems the earlier notes tracked (parts 1-8: redundant `_compute_obb`/`_compute_aabb`, `chain_objpegboards_for_point`, per-point binds) are fixed and no longer listed. What stays true and must not regress is in "Patterns that keep it fast".

## Line 3313-3412 (`resolve_rigid_move`), 3245-3308 (`resolve_local_move`), 3144-3240 (`_resolve_pinned_move`) — up to 18 evaluations per move when the move does not fit
The full move is tried first (one `_evaluate_points`). If it does not fit, the function evaluates t = 0 and then `iterations` midpoints (default 16, `resolve_rigid_move` line 3317), so up to 18 evaluations, and commits the best. A drag held at a limit, which is the normal case when someone pulls a wire taut, repeats that whole search on every mouse move, although the answer barely changes from one move to the next.
Fix: warm start from the previous move's accepted fraction (kept on the drag handler): test `t_prev + step` first; if it is infeasible and `t_prev` is feasible the answer is `t_prev` and it took two evaluations instead of eighteen. Fall back to the full search when the previous fraction is no longer feasible. No memory beyond one float per drag. This is the largest remaining multiplier in the file, because `_evaluate_points` is 735 lines (1704-2438) of Python with closures (`pull_node`, `eval_bundle_wire`, `place_pinned_loops`) defined on every call.

## Line 1704-2438 (`_evaluate_points`) — structural lookups repeated per evaluation
`pull_node` calls `_node_for_point` (line 1517) for each node it reaches, on every evaluation. `_node_for_point` goes through up to nine table selects (housings, terminals, cavities, transition branches, transitions, cable nodes, splices and service loops with `OR=True`, which scan their whole table; see `database/README.md`, finding 2). The answer depends only on the project's structure, which cannot change during a gesture, not on the move fraction, so it can be memoised per point for the whole drag in the same `chain_cache` dict the three resolvers already pass around. Memory: one small tuple per point reached in the drag (tens of entries).
`_lead_pieces` (line 1273) walks a cable lead piece by piece with an `OR=True` select on the service loops table at every step (line 1310): O(loops table) per step. Same remedy (index the OR, or cache per drag).

## Line 1023-1131 (`_anchor_index`, `_chains_for_point`) and 1136-1176 (`chains_bound_to_point`) — one index build per resolve call
`_anchor_index` builds a `point_id -> chains` map in one pass over every bundle and wire, once per `resolve_*` call through the shared `chain_cache`, so it is O(bundles + wires) per mouse move, then O(1). The chain structure does not change during a gesture either, so the index could be built once when the drag starts (the handler's `__init__`) and reused for every move: that moves an O(bundles + wires) pass out of the per-move path. Memory: one dict entry per anchor point in the project (a few KB to tens of KB).
`chains_bound_to_point` inspects the callbacks bound to a point (a short list); cheap.

## Line 2498-2673 (`_commit_points_body`) and 3013-3072 (`_commit_overlay`) — the winning candidate is written once
Each move commits only the best candidate, inside a gesture (`in_progress=True` uses the overlay and writes no rows; the real write happens in `finalize_drag`, line 3696). The commit suspends every affected chain's geometry rebuild (`suspend_updates` / `resume_updates`) so each wire is rebuilt once per move. Keep that.

## Patterns that keep it fast (do not regress)
- One `chain_cache` per resolve call passed to every `_evaluate_points` (a pure read-only solve; no writes until the winner is committed).
- `_move_point` skips a point that is already exactly where it is asked to go, so redundant callbacks cost nothing.
- Suspend/resume of a wire's or bundle's geometry rebuild around a batch of point moves, gated inside `_recalculate_geometry`.
- `WireSlackHandler` binds only the innermost point at each wire end, so one housing move fires one reconcile per wire.
- `chains_bound_to_point` (not an id lookup) decides which chains a moved point belongs to, because a structural stub can be a per-wire clone whose id the path table does not know.

## Line 3645-3691 (`realize_3d_move`), 3417-3512 (`realize_length_change`) — one evaluation each per call
Run once per drag step for a 3D move or a length change, not inside the search.
