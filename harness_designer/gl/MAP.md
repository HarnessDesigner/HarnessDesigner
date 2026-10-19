## FILES

#### __init__.py

Re-exports the `EVT_GL_*` string constants from `events.py` as the package's public event-name
surface (e.g. `EVT_GL_OBJECT_SELECTED`), so callers write `gl.EVT_GL_OBJECT_SELECTED` instead of
reaching into `gl.events` directly.

#### context.py

`GLContext` — thread-safe, re-entrant wrapper around a `QOpenGLWidget`'s `makeCurrent()`/
`doneCurrent()`. ⚠ It is `with`-only: public `acquire()`/`release()` were removed entirely and
renamed to private `_acquire()`/`_release()`, called only by `__enter__`/`__exit__`. This was a
deliberate fix (root-caused 2026-07-29) for a real class of random, hard-to-reproduce "context has
not been acquired" crashes (plus one "Cannot make QOpenGLContext current in a different thread"
crash): every old call site did `ctx.acquire(); <GL work>; ctx.release()` with no `try`/`finally`,
so any exception mid-block (including ones Qt's own signal/slot dispatch silently swallows)
skipped `release()` and permanently leaked the internal ref counter upward — a later `acquire()`
then wrongly believed the context was already current and skipped the real `makeCurrent()`,
surfacing as a crash at a completely unrelated later moment on whatever thread next touched that
context. Never add a new `.acquire()`/`.release()` pair for a `GLContext` — always
`with some_widget.context: ...` (safe to nest, safe across early returns/exceptions). This is
unrelated to `PooledVBOHandler`/`NonPooledVBOHandler`'s own, separate `.acquire()`/`.release()` in
`vbo.py`, which were deliberately left alone by that fix.

#### events.py

GL event system, ported from wx's `EVT_GL_*` custom events to PySide6 signals. The `EVT_GL_*`
constants are plain strings matching the Qt Signal names declared on `canvas_base.CanvasBase` —
pass one straight to `canvas.connect()`/`editor.connect()`. Event data classes `GLEvent`/
`GLObjectEvent`/`GLKeyEvent`/`GLCaptureLostEvent` (plus camera-specific `GLCameraEvent`) are plain,
wx-free Python objects carrying position/button-state/hit-object context; each extends a shared
`_GLEventBase.__init__` via `super()`. Imports `canvas_3d.camera` and `canvas_schematic.camera`
only under `TYPE_CHECKING`, for annotations only.

#### info.py

Queries OpenGL capability strings/limits. Ported from wx's "create a throwaway 1×1
`glcanvas.GLCanvas` purely to get a context, call `SetCurrent`, query GL strings" pattern to Qt's
`QOffscreenSurface` + `QOpenGLContext`, which needs no visible widget at all. The public API is
unchanged across the port: call `get(parent)` once to collect and cache, then call `get()` with no
argument to read the cached result.

#### object_picker.py

The one shared, camera-agnostic mouse-picking implementation used by all three canvases
(`canvas_3d`, `canvas_schematic`, `canvas_pegboard`) — duck-typed against `camera.modelview`/
`.projection`/`.viewport` plus a caller-supplied `get_view` callable, so it never needs to know
which concrete `Camera` subclass it's handed. `find_object()` is the main entry point;
`find_object_in_list()`/the private `_pick_candidates_at_mouse()` do the per-object screen-space
hit testing; `_unproject_from_ndc()` turns a normalized-device-coordinate point back into world
space via the inverse MVP matrix. As of the current `canvas_pegboard/mouse_handler.py` (confirmed
by reading it directly), pegboard's mouse handler is now just as thin as the other two editors'
and goes through this same shared module — the old pegboard-only `_find_anchor_at_point` AABB
hit-test MEMORY.md once flagged as the one remaining gap here is gone; all three editors now pick
through `object_picker` exclusively.

#### vbo.py

GPU vertex-buffer pipeline (~930 lines). Vertex attributes are local/model-space (vertex, smooth
normal, face normal); per-object transform (`objectPosition`/`objectRotation` as a scalar-first
`(w,x,y,z)` quaternion/`objectScale`) is applied in the shader via uniforms set only through the
`shaders.program.Program` mechanism — position/angle/scale changes never touch the VBO itself, only
uniform updates. `VBOHandlerBase.render(program, position, angle, scale, smooth)` takes the
`Program` object itself, not raw location ints. ⚠ The `vbo=None`/`_data` path assumes **world-space**
geometry: `_update_position` shifts `_data[0]` by the position delta AND re-applies the floor lock
on every write — any local-space user must override `_update_position` (see `Rings3D` in the
top-level `drag_handlers/` package, the current home for what used to be
`canvas_3d.rotation_rings`). ⚠ `Base3D.__init__`/`_update_position` apply a **floor lock** to any
object whose AABB dips below ground — UI gizmos must opt out via a `_floor_guard` during init plus
an `_update_position` override (see `Rings3D`/`Arrows3D`). `_MeshArena` is a managed GPU buffer
pool (one large arena buffer, sub-allocated per model) that tracks fragmentation of freed ranges
and compacts via GPU-to-GPU copies (`_gpu_copy`, no CPU round-trip) once a threshold is crossed.
`PooledVBOHandler` is a per-model-id refcounted singleton (`VBOSingleton` metaclass +
`acquire()`/`release()` — a different, unrelated pair from `GLContext`'s, deliberately kept as a
manual acquire/release) so every object sharing a model reuses the same uploaded GPU data;
`NonPooledVBOHandler` extends `VBOHandlerBase.render()` via `super()` for private, non-shared
single-buffer meshes (e.g. decals, gizmo geometry).

## FOLDERS

#### canvas_3d/

The free-orbit 3D editor's canvas package, built on `canvas_base/`. No longer contains
`rotation_rings.py`/`move_arrows.py`/`arcball.py`/a `dragging/` submodule — that interaction layer
was deliberately pulled out into the top-level `drag_handlers/` package (`editor_3d/`, plus shared
`move_arrows.py`/`wire_marker_arrow.py`) as part of an in-progress rebuild replacing `isinstance`
checks in the mouse handler with per-object-type polymorphism; this directory's own old
`mouse_handler.py`/`key_handler.py` equivalents are confirmed dead code today, fully superseded by
`canvas_base`'s shared `mouse_handler_base.py`/`key_handler.py`.

#### canvas_base/

The shared base-class package (`camera_base.py`, `canvas_base.py`, `canvas_window_base.py`,
`key_handler.py`, `floor_base.py`, `scene_light.py`, `mouse_handler_base.py`, `interaction.py`)
that `canvas_3d/`, `canvas_schematic/`, and `canvas_pegboard/` all subclass from. This is the
landed, renamed form of what MEMORY.md's "`gl/new_canvas_base` — the shared base class, started
(2026-08-12)" entry describes as just-starting scaffolding — on-disk evidence (directory names,
and a stray "`new_canvas2d` is dedicated to the flat schematic/pegboard views" comment still
sitting inside current `camera_base.py`) confirms the rename (`new_canvas_base`→`canvas_base`,
`new_canvas2d`→`canvas_schematic`, with `canvas_pegboard` kept as its own sibling rather than
merged into one combined 2D package) has fully landed; that MEMORY.md entry (and the sibling
"`new_canvas2d`: unifying schematic + pegboard canvases" entry) is now stale and a candidate for
removal/consolidation.

#### canvas_pegboard/

The Peg Board Editor's canvas package, built on `canvas_base/` — a top-down orthographic 2D view
sharing nearly all of its camera/canvas/window/mouse-handler code with `canvas_schematic/` (see
that folder's own duplication note under `floor.py`).

#### canvas_schematic/

The schematic editor's canvas package, built on `canvas_base/` — the renamed/landed form of the
old `canvas2d` directory described in the repo-root `CODEBASE_MAP.md`'s stale "## `gl/`" section
(that section's `canvas2d`/`canvas3d`/flat-`shaders/` layout no longer matches anything on disk).

#### culling/

One process-wide `CullingThreadPool()` instance (not per-canvas), reached through a
module-replacement singleton trick so `gl.culling.cull(...)` reads as a plain function call. Moved
out from under `gl/canvas_3d/` (superseding the old `canvas3d/culling.pyx` location MEMORY.md's
CullingThreadPool note still refers to by that old path) once it became clear canvas culling can
only ever run serially anyway (everything is on the main thread), making a per-canvas pool pure
duplication.

#### materials/

Weight-based material system, rewritt­en from scratch 2026-09-15 so that picking a color and
rendering it shows back that same color (see `material.py`'s own paragraph for the full
root-cause). Public single-`Color`-arg constructors (`materials.Plastic(color)` etc.) are
unchanged by the rewrite.

#### model_preview/

A small, standalone preview canvas, intentionally separate from the `canvas_base/`-derived
pipeline the three main editors share — see `canvas.py`'s own paragraph for a real latent risk
this separateness creates.

#### shaders/

All raw GLSL compiling/linking plus the `Program`/`ShaderProgram` wrapper classes that are meant
to be the *only* place in the app calling `GL.glGetUniformLocation`/raw `GL.glUniform*`/
`GL.glUseProgram` directly. ⚠ One piece of the repo-root `CODEBASE_MAP.md`'s old description of
this folder is now actively wrong, not just renamed: `shader_program.ShaderProgram` is NOT a
process-wide singleton — see `shader_program.py`'s own paragraph.
