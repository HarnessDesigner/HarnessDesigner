# harness_designer/drag_handlers/editor_pegboard/cable.py

## Line 116-161 (`__call__`, `_rope_call`) — per move: one rope-pull solve for the whole unit
With rope pull on, each move resolves the total mouse movement against every chain the dragged points touch (`resolve_rigid_move`), then sets every collected point with `point += Point(...)` while `WireSlackHandler._reconciling_any` is set so the points are not reconciled one by one. The solve is the dominant cost (see `handlers/rope_pull_handler.md`); the loop over points is `O(points)` times 20-70 us per `Point +=`. `sync_board_split_ends` runs after every move.
The flag handling is the right design: without it each point move would re-run the slack reconcile for its chains.

## Line 86-113 (`_rope_collect`) — once per drag
Builds the list of moving points (the plan's points plus, for a cable end, the whole end through `_cable_node`) with one `point.copy()` each and a `seen` set. Runs once at drag start. Not a concern.

## Line 116-129 (`__call__`, rope pull off)
Copies start and stop (two small arrays), runs the wire drag and calls `follow_drag('pegboard', ...)`. Cheap.

## `delete` — one extra solve at the end
On release it calls `resolve_rigid_move(..., in_progress=False)` once for the real (non-overlay) reconcile, so the bends get their layouts. One more solve per drag, not per move.
