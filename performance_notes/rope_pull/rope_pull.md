# harness_designer/rope_pull/rope_pull.pyx

The compiled port of `rope_pull_py.solve_chain` (Cython: `boundscheck=False`, `wraparound=False`, `cdivision=True`, `nonecheck=False`). `drag_end` is a plain `int` (0 start, 1 stop, 2 waypoint) and the boundary is tuples and lists, so there is no Python-object overhead beyond the `list` of waypoints it returns. The remaining cost per call is building those result tuples; the arithmetic is C. Registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS` (a hand-written `.pyx` must be, or a clean wheel build silently ships without it; per MEMORY.md).

## Cost
Microseconds per call; the number of calls per mouse move (see `handlers/rope_pull_handler.md`) is what to reduce, not this function.
