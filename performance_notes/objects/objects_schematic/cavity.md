# harness_designer/objects/objects_schematic/cavity.py

## Line 345-367 (`Cavity.render`, first frame) — good: self-replacing render
`render` computes the box once, then replaces itself on the instance with `_render_label` (line 365), so the first-frame check is never repeated. This is the right pattern and needs no change.

## Line 370-... (`_render_label`) — per-frame housing chain walk and `_is_180`
Each frame, `_render_label` reads `self.housing` (line 397), a property that walks `self.parent.housing` → facade → `.objschematic` every time. It also calls `_is_180(housing.angle.y)` (line 403) per frame. Both are cheap individually, but a housing carries many cavities, so this runs per cavity per frame. Caching the resolved housing on first use (it does not change after load) would remove the chain walk.

## Line 197-300 (`_rebuild_geometry`, `_compute_obb`, `_compute_aabb`, `hit_test_step2`/`3`) — bounds and hit tests
`hit_test_step3` is the per-pick path. It has the same full-mesh-per-call structure as the 3D `BaseVar.hit_test_step3` (see `objects_3d/base_3d.md`).
