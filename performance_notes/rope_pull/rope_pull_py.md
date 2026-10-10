# harness_designer/rope_pull/rope_pull_py.py

## Line 139-201 (`solve_chain`) — one pass over at most two spans
Builds a two- or three-point skeleton, then solves each span. It is O(number of spans) and runs once per solve. Called from the peg-board drag path many times per mouse move (see `handlers/rope_pull_handler.md`), so the per-solve constant matters. The work is a few `hypot` calls and a loop, which is cheap.

## Line 204-213 (`_polyline_length`) — Python loop over a short list
Two or three points. Fine.

## Line 216-283 (`_solve_span`) — the zigzag waypoints
Creates `count` bumps, where `count = ceil(excess / (2 * height_cap))`. The count grows as the slack grows and the height cap shrinks. With a normal height cap it is small.

**Edge case (flagged, not changed):** `height_cap = max(height_cap_fraction * straight, min_height_mm)` (line 241). If both `height_cap_fraction * straight` and `min_height_mm` are zero, `height_cap` is zero and line 244 divides by zero (`ZeroDivisionError`). That happens for coincident endpoints with a zero minimum height. The callers in this codebase pass a positive floor, but nothing enforces it.

Also, if `height_cap` is very small compared with the slack, `count` (and so the number of waypoints) can grow large. There is no upper bound on `count`.
