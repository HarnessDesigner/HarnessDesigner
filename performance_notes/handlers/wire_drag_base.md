# harness_designer/handlers/wire_drag_base.py

## Line 310-349 (`is_anchor_point`) — full scan of cavities and terminals per call
Loops over every cavity (line 336) and every terminal (line 340) in the project, checking a position id on each. It is a classmethod called once per point: from `wire_end_anchors` (line 380-381), and from `plan_wire_drag` for each moving point (line 425, 447). `plan_wire_drag` runs at drag start, so the cost is (points × (cavities + terminals)) once per drag. Building a set of anchor ids once per drag would make each check constant-time.

## Line 284-290 (`_is_in_view`) and 480-520 (`wire_layout_end_wire`) — loop over every wire
`wire_layout_end_wire` loops over `project.wires` (line 498) and calls `_is_in_view` on each (line 499). Runs when the wire-layout end is picked, not per move. Cost is linear in the number of wires.

## Line 793-860 (`_raw_move_delta`, `_move_delta`, `_apply_budget_clamp`) — per-move projection
`_raw_move_delta` projects the anchor, adds the raw mouse delta, and unprojects back. It runs on every mouse move during a wire drag. Each call makes a few matrix operations and calls the camera's projection methods. Fine.

## Line 872-934 (`_arm_drag`, `_disarm_drag`, `__call__`) — the drag hook
`__call__` runs on every mouse move during a drag. It computes the move delta, the budget clamp, and applies the points to each moving point (line 994 loop). The loop is linear in the number of moving points. Acceptable.

## Line 569-790 (`_view_merge_geometry`, `merge_wire_into`) — database writes on drop
Creates one merged row and rewrites route sets, then loops over `project.wire_markers` (line 779). Runs once on a wire-to-wire join. Fine.
