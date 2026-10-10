# harness_designer/add_handlers/editor_schematic/wire.py

## `hover` - per move (the most expensive path in this folder)
- `_pick_end` calls `find_object` on every move.
- In free space, `_blocked` calls `routing.free_segment_blocked`, which scans the project's housings and wires on every move.
- Over a snap target, `_preview_route_to` calls `routing.route`, an A* search (`heapq` in `wire_routing/routing.py`), run from the last waypoint on every move while the cursor stays over a terminal or splice.
- `_ghost_to` writes the loose end and calls `editor2d.Refresh(False)`, so the view repaints on every move.

Candidates to measure first:
1. Cache the route in `_preview_route_to` while the snap target and the last waypoint do not change. This is the largest possible saving, because A* runs on every move over a target.
2. Skip the repaint in `_ghost_to` when the loose end did not move.
3. Skip `free_segment_blocked` when the cursor is still in the same grid cell as the previous move.

Not on a hot path: `_click` (only on the click, plus one `hover` call), `_finish`, `_undo`, and `cancel`.
