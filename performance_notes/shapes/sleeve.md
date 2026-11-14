# harness_designer/shapes/sleeve.py

The solder-sleeve mesh: a hollow tapered tube revolved from `profile()`, built once at unit size and scaled by `(D, D, L)` through the pooled VBO `'sleeve'` (same pattern as `cylinder.py`). `sizes()` and `length()` are scalar helpers.

## `create` (resolution 48), `profile` — one-time mesh build
A revolve of a small profile at 48 steps: measured 768 vertices and 1,152 triangles, built once per process (cached through the pooled VBO and `mesh_cache`) and shared by every sleeve in the project, which is the right trade (one mesh in VRAM, scaled per object). Not per frame.

## `create_vbo`
Registers the mesh with `PooledVBOHandler`; the model-arena tiering applies (see `gl/vbo.md`). One handler for all sleeves, so the VRAM cost does not grow with the sleeve count.
