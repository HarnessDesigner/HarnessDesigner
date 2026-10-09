# harness_designer/objects/objects_3d/generic.py

`Generic` is a plain `Base3D` subclass with no render, update, or delete
overrides (checked with `dep_trace.py --overrides`). It inherits the draw and
update paths in `base_3d.md` unchanged. Its `__init__` wraps the super call in
`with parent.mainframe.editor3d.context:` (line 30), which is a one-time
construction cost, not a per-frame one.
