# harness_designer/objects/objects_schematic/terminal.py

## Line 847-... (`Terminal.render`) — up to three full render passes per terminal, every frame
The docstring says a terminal draws its name line(s), its "(" bracket, and its wire-stub cylinder, swapping `_vbo`/`_angle`/`_scale`/`_position` for each piece and delegating to the inherited pipeline. Each piece is a full `BaseVar.render` call, so one terminal can cost up to three complete passes per frame. Terminals are numerous (the docstring notes a housing can carry thousands), so this multiplies quickly.

The geometry itself is already handled well: the docstring explains that `_name_world_position`, `_bracket_world_position`, `_cylinder_world_start`, `_cylinder_world_angle`, and `_cylinder_length` are recomputed in `_rebuild_geometry` only when their inputs change, not every frame. So the remaining cost is the pipeline passes, the same per-object overhead described in `objectsvar/base_var.md`. Combining the three pieces into one batched draw per terminal (or per housing) would cut the pipeline overhead considerably.

## Line 881-887 — free-terminal early path
A free terminal (`_is_free`) draws through a single `super().render`, the cheapest path. No change needed.

## Line 583-666 (`_update_position`, `_update_angle`) — cascade from the housing on every move
Both call `_rebuild_geometry` (see the docstring at lines 871-876), which runs on every housing move or rotation. A housing move therefore re-derives geometry for every seated terminal. That is the correct behaviour, but it makes a housing drag O(terminals) per mouse event, the same shape as the cavity cascade.

## Line 784-847 (`_compute_obb`, `_compute_aabb`, `hit_test_step2`/`3`) — per-pick mesh path
`hit_test_step3` follows the same full-mesh structure as the other views' step 3 (see `objects_3d/base_3d.md`).
