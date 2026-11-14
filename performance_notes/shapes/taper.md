# harness_designer/shapes/taper.py

A hollow frustum (the 45-degree taper of a shield wire in the schematic), same pattern as `cylinder.py`: `create(radius, end_radius, height, resolution=360)` builds one unit mesh, `create_vbo` registers it as the pooled VBO `'taper'`, and objects scale it.

## `create` (resolution 360) — more segments than a few-pixel taper can show
Measured: 360 steps give 722 vertices and 720 triangles (about 26 KB at 36 bytes per vertex); 32 steps give 66 vertices and 64 triangles (about 2.4 KB). The mesh is built once and shared, so the cost is one time and tiny in memory; each taper drawn redraws 720 triangles, which is nothing for the GPU. A taper is a few pixels wide, so 32-48 steps would look the same, but the saving is small enough that this is the lowest priority item in the folder.
Built lazily by `objects_schematic/wire.py` `render` (not in `cache_primitives`), so the one-time build happens during the first frame that draws one (a hitch of a few milliseconds).
