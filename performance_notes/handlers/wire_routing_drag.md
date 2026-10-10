# harness_designer/handlers/wire_routing_drag.py

## Line 330-344 (`_update_hover`) - runs on every mouse move during a routed drag
`find_drop_hit` runs on every move (line 336). It calls `object_picker.find_object`, which is the full picker (see performance_notes/gl/object_picker.md), and then, for each eligible branch, a ray-sphere test through `_view_transition(...).hit_test_branch_ray` (line 204). The picker call dominates. The hover highlight is only redrawn when the target changes (line 339), which is the right guard. Caching the pick between moves while the cursor stays in one region would cut the per-move cost.

## Line 178-208 (`find_drop_hit`) - bundles first, then branches
The bundle check reuses the picker result, so no second pick is made for bundles. Branches are tested with a loop over eligible branches, each a ray-sphere test, so the cost is linear in eligible branches per move. The eligible set is small (only fitting bundle ends and branches), so this is fine.

## Line 108-... (`compute_eligible_targets`) - once per drag start
Walks project bundles and transitions once and checks freeness per end. The `is_in_*` checks it makes now read the view pools (see performance_notes/gl/camera notes), so this is one array read per object rather than a camera scan.

## `RouteSession.__call__` MOVE branch (2026-10-10 fix) - one extra static call per move, only while armed
Added `QtWidgets.QApplication.mouseButtons()` so a camera-move drag (any button) declines the event instead of being swallowed. That's a single Qt static-method call, not a query of any kind, paid once per mouse-move event while a session is armed (a rare, user-initiated, short-lived state) -- negligible next to the ray-sphere branch tests already below it.

## `_refresh_committed_wire` - one `refresh_waypoints()` call, once per committed route
Called exactly once per `RouteWalk.commit()` (either in `begin_route` for a single-hop route, or in `RouteSession.__call__`'s `LEFT_UP` once `self._walk.is_finished`), never per move. Cost is `Wire.refresh_waypoints`'s own (a waypoint rebind plus one `hidden_waypoint_ids` SELECT, see `performance_notes/handlers/wire_topology.md`) -- a one-shot cost at the end of a user-driven drag/click session, not a hot-path concern.
