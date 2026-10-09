# harness_designer/objects/objects_3d/transition.py

## Line 464-483 (`Branch.render`) — `create_vbo()` lookups and draw calls every frame
Each branch calls `_cylinder.create_vbo()` and possibly `_sphere.create_vbo()`
per frame, then draws its cylinder, plus a bulb cylinder and two spheres when
it has a bulb. `create_vbo()` is a cached global lookup, so the lookup itself is
cheap. The cost is the number of separate draw calls, roughly 2 to 4 per branch
per frame, which scales with branches per transition. `_use_body_model` already
skips the duplicate draw when a shared body mesh covers the branch, which is the
right optimization.

## Line 1028-1041 (`Transition._render_geometry`) — pure cache read, one draw per transition
Passes `material` and `branch_materials` into the VBO's `render()` each frame.
The override is cheap; it is the same shape as `BaseVar._render_geometry` with
extra arguments.

## Line 1054-1076 (`hit_test_branch`) — per-call allocation for the distance check
Computes `point.as_numpy - branch.tip_point.as_numpy` and a squared norm for
each branch that passes the sphere test. Fine for a handful of branches. It is
called from the drag path (per mouse move while dragging a wire end), so it is
a small per-move allocation on a hot path. Cheap enough that it is not worth
changing on its own.

## Line 1221-1246 (`Transition._update_angle`, `_update_position`) — both call `super()`
These go through `Base3D` and then `BaseVar`, which is the full update path
(context acquire, copies, `Refresh`). Each mouse-move event during a transition
drag pays that cost once per event. Not wrong, but a transition drag can
therefore trigger the GL-context acquire on every move. See `base_3d.md`.

## Known dead state (not a performance issue, noted for the functional review)
`_branch_points` and `_branch_diams` are always empty and never read; `get_branch`
declares `-> int` but returns a `Branch` (or implicitly `None`), and has zero
callers. Flagged in the earlier review, not changed here.
