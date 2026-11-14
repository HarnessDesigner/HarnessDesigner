# performance_notes/drag_handlers

Covers `harness_designer/drag_handlers/`. A drag handler is built when a drag starts and its `__call__` runs once for every mouse move until the drag ends. So `__call__` (and what it calls on each move) is the only hot path here. Construction and `delete` run once per drag.

Per-move costs that repeat across the editors:
- Projection of a point to screen space and back (`ProjectPoint` / `UnprojectPoint`): four camera calls and a few `Point` operations per move in the 3D base. Cheap in itself, but every `Point` `+`/`+=`/`@` costs 20-70 us (see `performance_notes/geometry/point.md`), so a handler that moves many points per frame (a rigid bundle move, a cable with its conductors) pays that per point per move.
- Snap probes and `find_object` picks in the wire drags. These are the expensive part of the wire drags. Not profiled.
- The rope-pull solver on the peg board (`resolve_rigid_move`, `resolve_local_move`). Its cost lives in `handlers/rope_pull_handler.py`; see that note. The pegboard `generic.py`, `bundle.py` and `cable.py` handlers are thin callers of it.
- Repaint requests after the position changes.
- Database writes: `begin_gesture()` / `end_gesture()` (3D `generic.py`, `waypoint.py`) bracket a drag as one write gesture, so a drag costs one commit, not one per move. That is the right design (MEMORY.md: SQLite commits cost per COMMIT); new handlers should do the same.

Status: static read of the code plus the shared `Point` benchmarks. Nothing in this folder has been profiled directly; the schematic `generic.py` carries its own `_TIMING` / `_PROFILE` switches for that.
