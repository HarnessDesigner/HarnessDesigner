## FILES

#### __init__.py

Docstring only -- imports nothing on purpose. `renderer.py` needs `pyopencl` and `bvh_processor.py` needs the
compiled `bvh` extension, and the app has to start without either, so the dialog
(`ui/dialogs/ray_tracing_dialog.py`) imports `scene`, `renderer` and `settings` itself when a render starts.
The old `RayTracingDialog` that lived in this package (`dialog.py`) was removed; the dialog is now in `ui/dialogs/`.

#### bvh.c

The Cython-generated C source compiled from `bvh.pyx`. Not hand-edited; regenerated whenever `bvh.pyx` changes.

#### bvh.pyx

The real Cython BVH builder -- OpenMP-parallel centroid calculation, GIL-free construction, pre-allocated
buffers, returns NumPy arrays for OpenCL compatibility. It compiles to `harness_designer.ray_tracing.bvh`
(`PyInit_bvh`; `builder/cython_build.py` lists it as `ray_tracing/bvh.pyx`), so it is imported as
`from . import bvh`. Its first comment says `# bvh_fast.pyx` -- stale; no module of that name exists, and
`import bvh_fast` (what `bvh_processor.py` used to do) can never work. It has to be compiled in place before
anything that builds a BVH can run (no `.pyd` is checked in -- `*.pyd` and the generated `bvh.c` are gitignored).
It is registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS`, so every wheel build compiles it with
the same flags as the rest (`builder/compiler.py`); for a dev checkout, the same `cythonize_to_c` + `compile_one`
steps with the output next to the source give `bvh.cp311-win_amd64.pyd` (compiled and smoke-tested 2026-10-31:
20k triangles -> 15k nodes in ~30 ms). The builder's flags have no `/openmp` / `-fopenmp`, so the `prange` loops
run serially in every build; that is fine at these sizes. `FastBVHBuilder` prints its own progress lines to stdout.

#### bvh_processor.py

`build_bvh(vertices, faces)` -- builds the single BVH over the whole merged scene with `bvh.FastBVHBuilder`.
One tree, because `kernel.cl` starts every ray at node 0. This replaced a threaded per-object builder
(`ThreadedBVHProcessor`) whose per-object trees were concatenated, so only the first object ever rendered.

#### kernel.cl

The OpenCL kernel `renderer.py` compiles and runs -- defines the `Material`/`Light` structs uploaded from
Python (`Material`'s scalar-weight layout is the one the 2026-09-15 material-system rewrite, see repo-root
`MEMORY.md`, made the rasterizer's own shaders match). The kernel has 51 parameters; the argument list in
`Renderer._render` must match it one for one. The hit normal is flipped to face the ray (triangle winding is
not guaranteed), and `safe_inverse` keeps the slab test from producing NaN for a ray component of exactly 0.
`enable_depth_of_field` and `shadow_softness` are passed but the kernel does not use them. The kernel also draws the 3D editor's floor as a plane (`floor_color`, a port of `gl/shaders/floor/fragment.frag`: checker tiles, solid major lines, dashed minor lines, anti-aliased from the pixel footprint on the plane) from `floor_params` (24 floats, `RenderSettings.floor_params`) plus the 32-bit dash pattern and phase as separate args; the floor is composited at its alpha (0.8 by default) over the background or over geometry behind it. When "Enable Reflections" is on and the camera is above the floor, a mirrored ray from the floor point is shaded with `shade_hit` (the per-hit shading, pulled out of `main` so it can run twice; lights are mirrored in the floor for it, as the rasterizer does) and shown through the translucent floor at 75%, like the viewport's mirrored copies. No shadows on the floor (the viewport has none either). Shading is meant to match the rasterizer (`gl/shaders/faces/fragment.frag`): lights are RGB (light colour multiplies diffuse and specular -- it was ignored before), a metal's highlight is tinted by its colour (`GLMaterial._metallic`), the Blinn-Phong exponent is 4x `shininess` to match the rasterizer's Phong highlight size, and on overflow all three channels are scaled together to keep the hue instead of clamping each. Reflection `fresnel` is only applied when reflections are enabled and falls back to the solid background colour when there is no env map or gradient (it used to blend toward black). A metal's reflection is tinted by its colour too (`mat.metallic`), or a polished copper wire end reflects the sky unchanged and renders pale blue. `Scene.add_object` skips objects whose `is_visible` is false (what the viewport does not draw). Not modelled: emissive/glowing materials (`GLMaterial.emissive` is not in the 12-float `Material` struct) and alpha (`transparency` is alpha, unused).

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

Results come back through three callbacks -- `on_chunk(start_y, rgb_uint8, percent)`, `on_finished(cancelled)`,
`on_error(exception)` -- all called **from the worker thread**, so a GUI must hand them over (the dialog uses Qt
signals). `cancel()` takes effect between chunks.

#### scene.py

`Scene` -- camera state plus the objects to render. `add_object(obj)` (GUI thread) copies the object's mesh
from `obj.vbo.vertices` -- a local-space triangle soup, three vertices per triangle, no index buffer -- and
applies scale, then `@ angle`, then position, the same way `BaseVar._compute_aabb` does, so no rotation
convention is re-derived here. `build()` (worker thread) merges everything, builds the one BVH, packs
materials (`GLMaterial.cl_array`) and lights, and makes the environment map. With no lights configured it
adds one at the camera. `SceneData` is what `build()` returns; `SceneObject` is the `Protocol` for what
`add_object` reads (`vbo`, `position`, `angle`, `scale`, `material`) -- any `BaseVar` qualifies. A wire or bundle is a chain of straight tubes (one per path segment) that all reuse one cylinder mesh, and its own position/angle/scale is only the straight start->stop chord, so those objects (and `WireStripe`, which yields nothing) provide `ray_trace_parts()` -- `(position, angle, scale, material)` per tube -- and `add_object` adds one copy of the mesh per part. Without it the whole bend would render as one straight cylinder. A part can also carry `(window, vbo)` (a wire's stripe): `_add_windowed` mimics the faces vertex shader -- keep helix triangles whose centre lies in the `[start, stop]` window along the wire, scale only X/Y, re-base Z to `start` -- and triangles that cross the window edge are cut exactly there (Sutherland-Hodgman), so a segment's stripe ends where the segment ends. With no lights, or `camera_light` set, a white light is added at the camera. A camera
`field_of_view` of 0.0 (the canvas has not drawn yet) falls back to 65 degrees (`Canvas.FOV_DEGREES`). The 3D canvas is a fixed oversized surface and the editor window shows a centred crop of it, so `Scene` takes the canvas and window sizes and `visible_field_of_view` narrows the field of view to the crop (same math as `CanvasWindow._apply_fit`); `fit_field_of_view` then widens it for an image narrower than the crop so nothing the user sees is cut off (a wider image shows extra at the sides). Without the sizes the whole canvas is framed.

#### settings.py

`RenderSettings._match_viewport()` (run when `Config.ray_trace.match_viewport`, default on) replaces the background with `Config.editor_3d.background_color` (flat: no gradient, no environment map) and describes `Config.editor_3d.floor` for the kernel. `RenderSettings` -- a plain-Python copy of `Config.ray_trace` made by `RenderSettings.from_config()` on the
thread that starts a render. `Config` is database backed and its connection must not be touched from the
render thread, so the worker only ever sees this snapshot.
