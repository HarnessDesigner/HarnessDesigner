# harness_designer/drag_handlers/editor_3d/__init__.py

## `_delta3d` - per move
Projects the anchor to screen space, adds the mouse delta, unprojects twice and subtracts the last position. Four camera calls and a few `Point` operations. Cheap.

## `_axis_locked_delta3d` - per move
Calls `_delta3d`, then (until the axis locks) counts settle events. After the lock it builds the move arrows once. No change.
