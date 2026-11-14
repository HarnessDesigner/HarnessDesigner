# harness_designer/drag_handlers/editor_3d/wire_service_loop.py

## Line 77-101 (`__call__`) — per move: slide along the wire, then update arrows and pegboard
Per move: `loop.slide_axle()` (the wire's local direction, recomputed every event because the wire turns around bends), `_line_latched_distance` (one ray-to-line distance, a few small NumPy arrays), `loop.slide_along_wire(distance)`, a `Point.copy()`, `_follow_loop` and `_realize_pegboard_length`. `_realize_pegboard_length` calls into the rope-pull solver for the chain anchored at the loop, so it is the expensive call here (see `handlers/rope_pull_handler.md`).
The cost of `slide_along_wire` itself lives in `objects/objects_3d/wire_service_loop.py` (see its note).

## Line 104-120 (`_follow_loop`)
Moves the arrow centre and re-reads the axle; the arrows are deleted and rebuilt only when the wire has turned by more than `_TURNED`, which is the right way to avoid per-move mesh rebuilds. Each rebuild creates new arrow objects, so a loop dragged around a tight bend pays that at each turn.
