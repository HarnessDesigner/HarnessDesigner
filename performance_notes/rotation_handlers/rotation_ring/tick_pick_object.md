# harness_designer/rotation_handlers/rotation_ring/tick_pick_object.py

## Line 55-90 (`TickPickObject`) — a pick proxy for one tick mark
A small object the picker can hit for a single tick. Created with the outer ring. `is_selected` is a flag, and its setter does nothing (`pass`). Cheap.

**Typing (fixed in this pass):** the setter declares `-> None`.
