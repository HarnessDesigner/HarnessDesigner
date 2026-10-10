# harness_designer/handlers/wire_slack.py

## Line 49-68 (`reconcile`) — runs once per wire, after both endpoints are known
Builds two `Line` objects and their lengths, then at most one waypoint. Not a per-frame path. Fine.

## Line 71-122 (`_add_waypoint_3d`, `_add_waypoint_pegboard`) — inserts a point, a path row, a layout and refreshes the view
Each call does one point insert, one path insert, one layout insert, one `WireLayout` construction, and a waypoint refresh on the view. These happen once per wire reconciliation. Fine for placement; not a loop.
