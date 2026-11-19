# harness_designer/database/project_db/housing_slots_pegboard.py (and housing_slots_base.py, housing_slots_schematic.py)

How it all works: section 15 of the module docstring of `database/project_db/pjt_housing.py`; this note is only the cost.

The peg board and the schematic housing move and rotate on pooled storage (built 2026-11-18, the same mechanism as the 3D view: `housing_slots.md`). Measured with the real `Point` / `Angle` classes, the real cascade methods of git HEAD against the new ones, and stand-in tables, interpreted, one frame of a housing with 100 cavities, 70 % of them with a terminal (some with seals):

| Frame | Old cascade | Now |
|---|---|---|
| Peg board rotate | 489 ms | 5.9 ms (83x) |
| Peg board move | 5.6 ms | 3.4 ms |
| Schematic rotate | 2.4 ms | 1.5 ms |
| Schematic move | 1.5 ms | 0.45 ms |

The old peg board rotate was the same cost as the old 3D one: three `Angle` setters per cavity, terminal and seal rebuilding a quaternion and a matrix. The schematic never had angles of its own below the housing, so its old cascade was already cheap and the gain is the plain point loop (a `Point` per point with `with pos:` and `float(str(axis))`) becoming array operations. The figures leave out what the callbacks run in the app (a wire rebuild, a database write per point).

## What a peg board move frame costs (measured with cProfile on the 100-cavity housing above, which has 181 clone points among its 714 point rows, probably more than a real one (a clone is a second wire on the same terminal); shares of the profiled frame)
- 39 % firing the callbacks of the pooled points (`_process_callbacks`: 24,000 firings in 30 frames, each walks the point's callback list).
- 25 % moving the clone points one at a time (`_move_children`: `Point` setters inside `with point:`); it is `_rotate_children`'s array form that the rotate frame uses.
- 17 % `_suspend_chains`: `chains_bound_to_point` reads every moved point's callback list (about 530 pooled points and 180 clones per frame). The chains found could be kept in the plan for the length of the gesture; a wire added during a gesture would be missed, which is why it is not done.
- 17 % `_write_points`: one `batch_update` row per bound point slot (about 530 rows). Both it and `_rotate_angles` (two strings per angle row) could be written once at the end of the gesture, the same open item as `housing_slots.md`.
- The clone-point query runs once per gesture (one `SELECT` per 400 parent rows); the schematic's `rotate` looks up the Z corrections (`housing.cavity_geometry`) only for a rotation to or from exactly 180 degrees.
