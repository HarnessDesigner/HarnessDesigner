# harness_designer/geometry/line.py

A `Line` is two `Point`s. Its cost per call is therefore the cost of the `Point` operations it makes (see [point.md](point.md): 20-70 us each) plus a few NumPy allocations, so a `Line` call is typically 50 to 200 us in the interpreter, not the "NumPy call overhead" the previous note assumed.

## Line 244-316 (`get_angle`, `set_angle`) and 519-546 (`get_rotated_line`) — two to four `Point.copy()` calls each
Each `copy()` is 3.5 us and the rotations go through `Point @ Angle` (66-70 us). `set_angle` is the most expensive (four copies). Used by drag and snap code per mouse move; a line rotated by an angle several times per move costs a few hundred microseconds. The fix is the Point/Angle one: faster arithmetic in `Point` and `Angle` helps every Line method.

## Line 549-626 (`get_parallel_line`), 629-662 (`__contains__`), 665-735 (`bow_midpoint`), 738-783 (`project_to_line`)
3 to 7 small NumPy allocations each. `__contains__` (point-on-segment test) and `project_to_line` are called by snap and projection code per mouse move; `bow_midpoint` is used by `rope_pull_py.solve_chain`'s single-bow case. These are one-shot math; batching several projections into one NumPy call would cut overhead only if a caller does many in a row (the pegboard `closest_point_on_chain` loops are the candidate; see `add_handlers/editor_pegboard`).

## Line 32-107 (`__array_ufunc__`) — nested loops with `float(str())` and `tolist()`
Only for NumPy expressions containing a `Line`; not a frame-rate path.

## Memory
A `Line` holds two `Point`s and nothing else. The `Point`s of an unregistered line are not cached, so lines created during a drag are garbage collected immediately.
