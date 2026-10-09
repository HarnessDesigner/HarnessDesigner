# harness_designer/objects/objects_3d/seal.py

No per-frame override of `render`, `_update_position`, `_update_angle`, or
`_update_scale` in this file (checked with `dep_trace.py --overrides`). It
inherits the `Base3D`/`BaseVar` draw and update paths, so the costs in
`base_3d.md` (per-object `with shaders.faces:` churn, the GL-context acquire on
position events) apply unchanged.

Not analysed line by line for performance. Any file-specific hot path would show
up as an override of one of the hooks above or in a menu callback, and none were
found here. Re-check if this file gains a `render` override.
