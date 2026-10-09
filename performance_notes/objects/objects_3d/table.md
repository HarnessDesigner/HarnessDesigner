# harness_designer/objects/objects_3d/table.py

Inert placeholder: `Table.__init__` passes `None` for vbo, angle, position,
scale, and material, and sets `_is_visible = False` (line 39). `BaseVar.render`
returns early on `vbo is None`, so this object does no per-frame work. No
performance concerns.
