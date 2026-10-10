# harness_designer/handlers/wire_routing_handler.py

## Line 135-185 (`check_view`, `_points_table`, `_bundle_end_point_id`, `_branch_point_id`, ...) — small accessors
Each returns one id or table reference. Called per hop while a route is built. Cheap.

## Line 355-370 (`_branch_at_point`) — one SELECT per call
`ptables.pjt_transition_branches_table.select('id', **{column: point_id})` runs once per call. It is called per hop while a route is walked (line 501 for the far branch). A route crosses only a few transitions, so the cost is a few queries per route.

## Line 422-602 (`RouteWalk`, `choose`, `commit`) — the route state machine
`RouteWalk` steps through the hops of a route, and `_advance` loops over waypoint ids (line 495). Runs when a route is built. Cost is linear in the number of waypoints on the route.

## Line 603-660 (`route_wire`) and 660-end (`_commit_route`) — the commit path
`route_wire` is called from `_commit_route` (line 595), which runs on release. It creates two guard points and rewrites route rows for the view, plus a loop over existing interior rows (line 679-685). None of this runs per mouse move. Fine.

## Line 264-355 (`_centroid`, `compute_guard_position`, `compute_housing_breakout_point`) — geometry on demand
Plain NumPy geometry, called when a guard point is computed. Fine.

**Note on the hover path:** the per-move work for routed-wire placement lives in `wire_routing_drag.py` (see that note), not here.
