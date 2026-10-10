# harness_designer/add_handlers/editor_3d/cover.py

## `snap_pool` property - rebuilt on every hover
`hover` reads `self.snap_pool`, which loops over every project housing, filters on `is_in_3dview`, collects `cover_position3d` into a list, and builds a new `SnapPool` (and its `np.array`). That is O(housings) Python work plus an allocation on every mouse move.
Candidate: build the pool once in `__init__` (or on the first `hover`) and invalidate it when `is_in_3dview` or a housing's cover position changes. The housing set does not change during a session, so one build should suffice. Needs a measurement with a realistic housing count.

## `hover` - per move
Then `snap_pool.query(world_pos)` (vectorised), and `set_angle_from_housing` only when the snapped housing changes. Fine.
