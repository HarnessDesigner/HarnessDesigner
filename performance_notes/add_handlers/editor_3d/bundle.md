# harness_designer/add_handlers/editor_3d/bundle.py

## `Bundle.hover` - per move
Every move wraps the work in `with self.mainframe.editor3d.context:`, which makes the GL context current on every move. It is needed because `_move_growing_point` writes positions that the 3D view reads. Candidate: check whether the context is needed for the position write itself.
`hover` also calls `_find_free_branch_ray` (a ray test across the project's free branches) and `build_ray`. Both run per move. The branch count is small, so the ray test is cheap.

## `_seed_pegboard` and `_finish_common` - once per placement
These walk the 3D path and insert peg-board rows. They run once at the end of a placement, so they are not a concern.

## `_narrow_diameter_range` - once per branch attach
It refreshes every committed layout's diameter. The list is short, so it is not a concern.
