# harness_designer/drag_handlers/editor_3d/waypoint.py

Drag of a cable waypoint (a cable has no layout to hold the point, so the drag holds the row itself).

## Line 27-41 (`__init__`) — one DB lookup and one gesture per drag
Looks up the `pjt_points3d` row once and opens a write gesture (`begin_gesture`); `delete` closes it. One commit for the whole drag, which is the right shape.

## Line 52-59 (`__call__`) — per move
One `_axis_locked_delta3d`, one `Point +=` and one `Point.copy()` (3.5 us). The `+=` writes the DB row through the point's bound callback while the gesture is open. Cheap.
