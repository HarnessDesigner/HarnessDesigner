# harness_designer/rope_pull/rope_pull_py.py

The pure-Python reference for the rope-pull span solver (`solve_chain`, `_solve_span`). The compiled port (`rope_pull.pyx`, see `rope_pull.md`) is what the app calls when it is built; this version is the reference it is checked against. Pure scalar math on `(x, z)` tuples, no NumPy, which is the right shape for many tiny calls (MEMORY.md).

## Line 144-211 (`solve_chain`), 228-297 (`_solve_span`) — O(spans) plus O(zigzag count)
Builds a two- or three-point skeleton, then for each span computes the bump count and places the zigzag waypoints with one loop of `count` iterations. The count is now bounded (`max_count = floor(straight / spacing)`, so it cannot grow without limit), and a zero straight length is handled (`straight < _EPS`). The earlier notes about a possible division by zero and an unbounded count no longer apply. Cost per solve is a few `hypot` and `sqrt` calls plus the waypoint loop; `handlers/rope_pull_handler.py` calls it many times per mouse move (up to 18 `_evaluate_points` passes, see its note), so the constant matters but the function itself is cheap.
