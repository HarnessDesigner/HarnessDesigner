# harness_designer/handlers/wire_topology.py

## Line 27-70 (`segment_index`) — one pass over one wire's segments
Builds the point list for the chosen view, then finds the nearest segment. Runs on a split or insert, and from `wire_routing_handler` (see that module's notes). Cost is linear in the number of waypoints on one wire. Fine.

## Line 76-192 (`split_wire_at_point`) — creates two wires and walks every marker
Creates two wire rows, four 2D and 3D route sets, and then loops over `project.wire_markers` (line 179) to re-home markers. The marker loop is linear in the number of markers in the project. This runs on a user action (splice or service-loop insertion), not per frame. Fine.

## Line 198-288 (`merge_wires`) — creates one wire and walks every marker
Same shape as `split_wire_at_point`: one merged row, two route sets, a loop over every marker. Runs on a user action. Fine.

## `hidden_waypoint_ids` — one SELECT per call, but never per frame
Runs `pjt_wire_paths_table.for_wire(wire_id, view)` (one SELECT) and a linear scan of the returned rows. The only callers are `objects.objects_3d/objects_pegboard.wire.Wire._bind_waypoints`, which runs on construction and on every `refresh_waypoints()` call (a waypoint add/remove/reorder), never from `render`/`hit_test_step3`/`_segment_transforms` directly -- those read the cached `self._hidden_waypoint_ids` set instead, an O(1) membership test per segment. Cost is linear in the wire's own route length, paid once per topology change, not once per frame. Fine.
