# performance_notes/drag_handlers

Covers `harness_designer/drag_handlers/`. A drag handler is built when a drag starts and its `__call__` runs once for every mouse move until the drag ends. So `__call__` (and the helpers it calls on each move) is the only hot path here. Construction and `delete` run once per drag.

Per-move costs that repeat across the editors:
- Projection of a point to screen space and back (`ProjectPoint` / `UnprojectPoint`). Two of each per move in the 3D base. Cheap.
- Snap probes and `find_object` picks, in the wire drags. These are the expensive part. Not profiled.
- Repaint requests after the position changes.

Status: static read of the code only. Nothing here has been profiled.
