# harness_designer/ray_tracing/scene.py

Collects world-space triangles from the scene objects and flattens them into the arrays the kernel needs.

## Line 257-283 (`_local_mesh`) — a copy of every object's vertices
`np.array(data[:count], dtype=np.float32)` copies the model's vertex data (and builds a normals array) for each object added, on the GUI thread (`Scene.add_object`). Instances of the same model get one copy each. A model used by 500 housings is copied 500 times before the world transform. For a large scene this is the main host-memory cost and the main GUI-thread wait before a render starts.
Fix: keep one local mesh per model (keyed by the VBO) and apply each instance's transform when building the world-space arrays in `build`. Saves memory proportional to the instance count; costs a lookup per object.

## Line 363-411 (`build`) — one concatenate, and the faces are an `arange`
`np.concatenate(self._vertices)` copies everything once more (peak is twice the mesh); `faces = np.arange(len(vertices)).reshape(-1, 3)` gives every triangle its own three vertices (no sharing), so a mesh is stored non-indexed: 36 bytes of positions plus 36 bytes of normals per triangle, plus 12 bytes of face indices and 4 of object id. A scene of 5 million triangles is about 290 MB of arrays, held again on the device. Indexing would shrink positions by roughly the share of vertices that are shared (about 6x for a closed mesh) at the cost of building the index; the kernel reads `faces` already, so it could take an indexed layout.
`build_bvh` (see `bvh.md`) runs here, once per render.

## Line 330-360 (`load_environment_map`, `generate_environment`)
Image work when a render is set up. Not per frame.
