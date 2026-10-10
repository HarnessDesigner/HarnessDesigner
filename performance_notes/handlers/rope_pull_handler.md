# harness_designer/handlers/rope_pull_handler.py

## Line 838-929 (`resolve_rigid_move`) — up to 34 full evaluations per mouse move
This is the largest cost in the handlers folder, and it runs on every mouse move of a peg-board rigid drag. When the full move does not fit (line 906-909), the function does a binary search over the move fraction. It evaluates the endpoints (line 913) and then `iterations` midpoints (line 915-924). `iterations` defaults to 32 (line 842), so a move that does not fit costs up to 34 evaluations.

Each evaluation calls `_evaluate_points` (line 624), which calls `_chains_for_point` (line 314) for every point it moves (line 749).

## Line 314-357 (`_chains_for_point`) — full scan of the bundles and wires tables per point
For each point, the function iterates over every row of `pjt_bundles_table` (line 343) and every row of `pjt_wires_table` (line 350), and calls `_drag_end_for` on each. The cost is (bundles + wires) per moved point, per evaluation. With 34 evaluations per move, that is 34 × points × (bundles + wires) row visits per mouse move.

The move fraction does not change which chains touch a point, so the chain list could be built once per drag (per moved point) and reused across the whole search. That is the single change with the largest payoff in this folder.

## Line 933-end (`realize_length_change`, `realize_3d_move`) — one evaluation each
Runs once per drag step for length changes and 3D moves, not inside the search. Cost is one `_evaluate_points` plus one `_commit_points`. The same `_chains_for_point` scan applies.

## Line 175-313 (`_reconcile_interior`) — database writes on commit
Inserts points and layouts for new interior positions and removes old ones. Runs once per commit. The `in_progress` flag exists to avoid DB churn while the mouse is still moving (see the module docstring). Fine.

## Line 360-end — layout and geometry helpers
`_rotated_and_translated`, `_fixed_count_span`, `_fixed_count_interior` are per-span geometry. They are called from inside the evaluation, so they are on the per-move path, but each call is small.
