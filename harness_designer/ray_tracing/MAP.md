## FILES

#### __init__.py

Docstring only -- imports nothing on purpose. `renderer.py` needs `pyopencl` and `bvh_processor.py` needs the
compiled `bvh` extension, and the app has to start without either, so the dialog
(`ui/dialogs/ray_tracing_dialog.py`) imports `scene`, `renderer` and `settings` itself when a render starts.
The old `RayTracingDialog` that lived in this package (`dialog.py`) was removed; the dialog is now in `ui/dialogs/`.

#### bvh.c

The Cython-generated C source compiled from `bvh.pyx`. Not hand-edited; regenerated whenever `bvh.pyx` changes.

#### bvh.pyx

The real Cython BVH builder -- GIL-free construction, pre-allocated buffers, returns NumPy arrays for OpenCL compatibility. Median split on the longest axis of each node, done with a quickselect (`select_nth_nogil`, O(n) per level; it used to fully sort every node's range, O(n log n) per level) over per-triangle boxes computed once in `__init__` (`tri_bounds`; before, each node re-read nine scattered vertex coordinates per triangle). The tree's shape depends only on the triangle count, so `count_nodes(n)` gives every subtree its own range of node indices up front: the top `PARALLEL_SPLIT_DEPTH` (6) levels are built on one thread, which only notes the 64 subtrees below, and `build()` then builds those on a `ThreadPoolExecutor` (`_build_task` holds no GIL). A thread pool and not `prange`, because the builder has no OpenMP (below). Under `PARALLEL_MIN_PRIMITIVES` (20000) it is all one thread. Measured 1.2M triangles: 2.5 s -> 0.6 s; node numbering is still pre-order (left child = node + 1) and the output arrays are unchanged, so `kernel.cl` needs nothing. Recompile after editing it (a running app keeps the old `.pyd` loaded and Windows will not let the compiler delete it: rename the file first). It compiles to `harness_designer.ray_tracing.bvh`
(`PyInit_bvh`; `builder/cython_build.py` lists it as `ray_tracing/bvh.pyx`), so it is imported as
`from . import bvh`. Its first comment says `# bvh_fast.pyx` -- stale; no module of that name exists, and
`import bvh_fast` (what `bvh_processor.py` used to do) can never work. It has to be compiled in place before
anything that builds a BVH can run (no `.pyd` is checked in -- `*.pyd` and the generated `bvh.c` are gitignored).
It is registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS`, so every wheel build compiles it with
the same flags as the rest (`builder/compiler.py`); for a dev checkout, the same `cythonize_to_c` + `compile_one`
steps with the output next to the source give `bvh.cp311-win_amd64.pyd` (compiled and smoke-tested 2026-10-31:
20k triangles -> 15k nodes in ~30 ms). The builder's flags have no `/openmp` / `-fopenmp`, so the `prange` loops
run serially in every build (`calculate_centroids_parallel` and the bounds loop are cheap, so that is fine). `FastBVHBuilder` prints its own progress lines to stdout.

#### bvh_processor.py

`build_bvh(vertices, faces)` -- builds the single BVH over the whole merged scene with `bvh.FastBVHBuilder`.
One tree, because `kernel.cl` starts every ray at node 0. This replaced a threaded per-object builder
(`ThreadedBVHProcessor`) whose per-object trees were concatenated, so only the first object ever rendered.

#### kernel.cl

The OpenCL kernel `renderer.py` compiles and runs -- defines the `Material`/`Light` structs uploaded from
Python (`Material`'s scalar-weight layout is the one the 2026-09-15 material-system rewrite, see repo-root
`MEMORY.md`, made the rasterizer's own shaders match). The kernel has 58 parameters; the argument list in
`Renderer._render` must match it one for one. The hit normal is flipped to face the ray (triangle winding is
not guaranteed), and `safe_inverse` keeps the slab test from producing NaN for a ray component of exactly 0.
`enable_depth_of_field` and `shadow_softness` are passed but the kernel does not use them. The kernel also draws the 3D editor's floor as a plane (`floor_color`, a port of `gl/shaders/floor/fragment.frag`: checker tiles, solid major lines, dashed minor lines, anti-aliased: the pixel's footprint along each floor axis comes from the floor points under the neighbouring pixels, like GLSL `fwidth`, the pattern is averaged over `FLOOR_SAMPLES` x `FLOOR_SAMPLES` sub-pixel samples, and the dash pattern fades to its average coverage once a bit of it is finer than the footprint) from `floor_params` (24 floats, `RenderSettings.floor_params`) plus the 32-bit dash pattern and phase as separate args; the floor is composited at its alpha (0.8 by default) over the background or over geometry behind it. When "Enable Reflections" is on and the camera is above the floor, a mirrored ray from the floor point is shaded with `shade_hit` (the per-hit shading, pulled out of `main` so it can run twice; lights are mirrored in the floor for it, as the rasterizer does) and shown through the translucent floor at 75%, like the viewport's mirrored copies. No shadows on the floor (the viewport has none either). Shading is meant to match the rasterizer (`gl/shaders/faces/fragment.frag`): lights are RGB (light colour multiplies diffuse and specular -- it was ignored before), a metal's highlight is tinted by its colour (`GLMaterial._metallic`), the Blinn-Phong exponent is 4x `shininess` to match the rasterizer's Phong highlight size, and on overflow all three channels are scaled together to keep the hue instead of clamping each. Reflection `fresnel` is only applied when reflections are enabled and falls back to the solid background colour when there is no env map or gradient (it used to blend toward black). A metal's reflection is tinted by its colour too (`mat.metallic`), or a polished copper wire end reflects the sky unchanged and renders pale blue. `Scene.add_object` skips objects whose `is_visible` is false (what the viewport does not draw). Normals: `shade_hit` keeps the triangle's FACE normal (cross product of its edges, flipped toward the viewer) for geometry -- shadow rays and ambient occlusion are offset along it and the hit point is snapped onto its plane -- and shades with a SHADING normal: for an object the viewport draws smooth (`smooth` true; a wire's stripe always) the VBO's per-vertex `smooth_normals`, blended by the barycentric weights of the hit point (computed from cross products, since a wire's sliver triangles lose their precision to cancellation in the dot-product form), put on the face normal's side, and used for diffuse, specular, the reflection vector and fresnel. A zero vertex normal (a flat object, or a VBO with fewer normals than vertices) makes it fall back to the face normal. Precision: a ray starts where it reaches the scene's bounding box (`approach_distance`), not at the camera, because with the camera tens of metres away every `origin - vertex` subtraction is off by ~2e-3 mm, as wide as a wire's thin triangles -- the camera ray then misses the near wall and hits the inside of the far one, which shadow rays correctly darken (black speckles on distant wires). The hit point is also snapped onto its triangle's plane and shadow rays are offset by `shadow_bias` (scales with the coordinates). Multisampling: `RenderSettings.samples` passes per pixel; each pass jitters the ray inside the pixel (`pixel_jitter`, an R2 sequence shifted per pixel) and `store_pixel` folds it into a running average in the band buffer (a non-finite colour is dropped). Not modelled: emissive/glowing materials (`GLMaterial.emissive` is not in the 12-float `Material` struct) and alpha (`transparency` is alpha, unused).

#### light.py

`Light` -- position/intensity/color; `to_array()` flattens it into the layout the OpenCL kernel expects, so
lights can be uploaded as plain float arrays.

#### renderer.py

`Renderer` -- picks the OpenCL device (GPU first, then CPU), compiles `kernel.cl`, and renders on a worker
thread one band of rows at a time. `__init__` runs on the GUI thread: `_detect_gpu` makes a throwaway
`QOpenGLContext` current and runs `gpu.GPU.detect()`, because that call finds the vendor from `glGetString`,
which answers only on a thread with a current GL context -- without one it silently uses `GPU._fallback()`'s
made-up 4 GiB / 2 GiB (the app's own `memory_diagnostics.py` hit the same trap). That gives the real VRAM
total/used from the display driver (NVAPI / ADL / GL extension; verified live on a Quadro RTX 4000). A CPU device,
an unrecognised vendor or any failure falls back to OpenCL's `global_mem_size` figures (half of it counted free).

`start()` spawns the thread, which builds the scene, uploads it and loops over the chunks. The rows per launch
come from `_chunk_rows`: the smallest of (free memory x `MEMORY_FRACTION` minus the uploaded scene buffers) / row
size, `max_mem_alloc_size` / row size (one OpenCL buffer is often capped at a quarter of VRAM -- 2 GiB of 8 on the
dev machine, which the old sizing could exceed on a 32K image), and `MAX_PIXELS_PER_CHUNK` (1M). The pixel cap is
there because memory is not the only reason to split: a single launch over a big image reports no progress and
risks the OS resetting a busy display GPU (Windows TDR); before it, any image that fit in memory (everything up to
and past the 7680x3268 default) rendered as ONE launch, so incremental display never happened. `gpu.GPU.
get_chunk_size` is no longer used (it counts only the output buffer and ignores the scene).

The vertex-normal buffer (or its stand-in) is the second upload, after `vertices`, and its buffer and `has_vertex_normals` are the last two kernel arguments. Each band is rendered in `samples` passes (separate launches, each followed by `queue.finish()`); the band is copied back and reported after the last pass and at most every `PREVIEW_INTERVAL` seconds in between, so a long multisampled render keeps refining the picture. Results come back through three callbacks -- `on_chunk(start_y, rgb_uint8, percent)`, `on_finished(cancelled)`,
`on_error(exception)` -- all called **from the worker thread**, so a GUI must hand them over (the dialog uses Qt
signals). `cancel()` takes effect between chunks.

#### scene.py

`Scene` -- camera state plus the objects to render. `add_object(obj)` (GUI thread) copies the object's mesh
from `obj.vbo.vertices` -- a local-space triangle soup, three vertices per triangle, no index buffer -- and
applies scale, then `@ angle`, then position, the same way `BaseVar._compute_aabb` does, so no rotation
convention is re-derived here. `build()` (worker thread) merges everything, builds the one BVH, packs
materials (`GLMaterial.cl_array`) and lights, and makes the environment map. With no lights configured it
adds one at the camera. `SceneData` is what `build()` returns; `SceneObject` is the `Protocol` for what
`add_object` reads (`vbo`, `position`, `angle`, `scale`, `material`) -- any `BaseVar` qualifies. A wire or bundle is a chain of straight tubes (one per path segment) that all reuse one cylinder mesh, and its own position/angle/scale is only the straight start->stop chord, so those objects (and `WireStripe`, which yields nothing) provide `ray_trace_parts()` -- `(position, angle, scale, material)` per tube -- and `add_object` adds one copy of the mesh per part. Speed: a mesh is read from its VBO once per scene (`_meshes`, keyed by `id(vbo)`; every segment of every wire shares one cylinder and one helix), and the helix is indexed once as a `_WindowedMesh` (triangles sorted by lowest Z, so a window is a binary search plus a slice instead of a scan over the whole helix -- which is as long as the longest wire's stripe -- per segment). `_clip_triangles` cuts all the crossing triangles of a window at once in numpy (it replaced a Python Sutherland-Hodgman loop, ~0.25 s per 60 segments). The stripe is ~67 triangles per mm of wire and is 99.9% of a wire scene's triangles. Objects the viewport draws smooth (`obj.smooth`, False when the attribute is missing, as in `Base3D`; a windowed stripe is always smooth) also keep the VBO's `smooth_normals`, carried to world space by `_world_normals` -- divided by the scale, rotated by `angle`, re-normalised, exactly what `gl/shaders/faces/vertex.vert` does -- and `build()` concatenates them into `SceneData.vertex_normals` (zero rows for flat objects, `None` when nothing is smooth so the renderer uploads a 3-float stand-in instead of a second vertex-sized buffer). `_add_windowed` clips position and normal together so a cut triangle's normals blend across the cut. Without it the whole bend would render as one straight cylinder. A part can also carry `(window, vbo)` (a wire's stripe): `_add_windowed` mimics the faces vertex shader -- keep helix triangles whose centre lies in the `[start, stop]` window along the wire, scale only X/Y, re-base Z to `start` -- and triangles that cross the window edge are cut exactly there (Sutherland-Hodgman), so a segment's stripe ends where the segment ends. With no lights, or `camera_light` set, a white light is added at the camera. A camera
`field_of_view` of 0.0 (the canvas has not drawn yet) falls back to 65 degrees (`Canvas.FOV_DEGREES`). The 3D canvas is a fixed oversized surface and the editor window shows a centred crop of it, so `Scene` takes the canvas and window sizes and `visible_field_of_view` narrows the field of view to the crop (same math as `CanvasWindow._apply_fit`); `fit_field_of_view` then widens it for an image narrower than the crop so nothing the user sees is cut off (a wider image shows extra at the sides). Without the sizes the whole canvas is framed.

#### settings.py

`RenderSettings._match_viewport()` (run when `Config.ray_trace.match_viewport`, default on) replaces the background with `Config.editor_3d.background_color` (flat: no gradient, no environment map) and describes `Config.editor_3d.floor` for the kernel. `RenderSettings` -- a plain-Python copy of `Config.ray_trace` made by `RenderSettings.from_config()` on the
thread that starts a render. `Config` is database backed and its connection must not be touched from the
render thread, so the worker only ever sees this snapshot.
