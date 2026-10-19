## FILES

#### __init__.py

Re-exports `RayTracingDialog` from `dialog.py` as the package's one public entry point.

#### bvh.c

The Cython-generated C source compiled from `bvh.pyx` into the `bvh_fast` extension module. Not hand-edited;
regenerated whenever `bvh.pyx` changes.

#### bvh.pyx

The real Cython BVH builder — OpenMP-parallel centroid calculation, GIL-free construction, pre-allocated
buffers, returns NumPy arrays for OpenCL compatibility. **This file's own module-level comment reads
`# bvh_fast.pyx`** — the source file on disk is named `bvh.pyx`, but it compiles to and is imported
everywhere as `bvh_fast` (`import bvh_fast` in `bvh_processor.py`). The filename and the importable module
name do not match; don't assume `import bvh` will work.

#### bvh_processor.py

`ObjectData`/`ProcessedObject` dataclasses plus the threaded driver that transforms each object's geometry
(via `bvh_fast.quaternion_to_rotation_matrix`/`apply_transform_parallel`) and builds its acceleration
structure (`bvh_fast.calculate_centroids_parallel`, `bvh_fast.FastBVHBuilder`) on worker threads.

#### dialog.py

`RayTracingDialog(QtWidgets.QDialog)` — displays render progress, previews the in-progress image, and
exposes save/settings actions. Owns the `Renderer`/`Scene` objects and reads `Config.ray_trace` settings.

#### kernel.cl

The OpenCL kernel `renderer.py` compiles and runs — defines the `Material`/`Light` structs uploaded from
Python (`Material`'s scalar-weight layout is the one the 2026-09-15 material-system rewrite, see repo-root
`MEMORY.md`, made the rasterizer's own shaders match).

#### light.py

`Light` — position/intensity/color; `to_array()` flattens it into the layout the OpenCL kernel expects, so
lights can be uploaded as plain float arrays.

#### renderer.py

`Renderer` — compiles the OpenCL kernel (`kernel.cl`) and executes chunked ray-tracing work against a
prepared `Scene`, invoking a callback per rendered chunk. Chunk height comes from
`harness_designer.gpu.GPU.get_chunk_size()` so a render doesn't try to allocate more VRAM than is actually
free — see `../gpu/MAP.md` for that calculation's own caveats (an "unknown"-semantics `multiplier`
parameter feeding into the VRAM estimate it's ultimately based on).

#### scene.py

`Scene` — assembles geometry/lighting/camera state into whatever `Renderer` needs. `SceneObject` is a
`Protocol` describing what `Scene.build()` reads off each object added to the scene (`vertices`, `faces`,
`normals`, `position`, `angle`, `material`) — any object with those attributes can be ray-traced, not just a
specific class hierarchy.
