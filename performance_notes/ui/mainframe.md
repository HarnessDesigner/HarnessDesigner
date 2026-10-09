# harness_designer/ui/mainframe.py

## Reviewed
The bounds save path, the event handlers, the clone and handler setters, and the active-canvas lookup were read. The file is 3,429 lines and was **not** read in full for performance, so this note does not cover the project load and unload sequence in detail.

## `_save_project_bounds` - runs once, on the shutdown path
Each of the three views computes its AABB extent and stores it as a list. The cost is three small conversions, once per unload, so there is nothing to change. The change in this pass replaced a `setattr` loop with three explicit assignments; the behaviour is the same, and the failure policy (log and continue, so shutdown is never blocked) is unchanged.

## `set_clone_obj` / `get_clone_obj` / `set_obj_handler` - fan-out setters
`set_clone_obj` forwards to three editor panels, and `set_obj_handler` cancels the previous handler before installing the new one. Both run per user action, not per frame, so there is nothing to change.

## `SetStatusText` - no callers
`SetStatusText` has no callers in the package, so it is dead code. Its unused second parameter is now annotated `None`, which is the only value its signature accepts.
