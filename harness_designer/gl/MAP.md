## FILES

#### __init__.py

Re-exports the `EVT_GL_*` string constants from `events.py` as the package's public event-name
surface (e.g. `EVT_GL_OBJECT_SELECTED`), so callers write `gl.EVT_GL_OBJECT_SELECTED` instead of
reaching into `gl.events` directly.

#### arena_buffer.py

The GPU side of the pooled arenas and the idle-time maintenance both pools share (new 2026-11-08, pulled out of `vbo.py` when the
wire pool was added so the two pools work the same way). `BufferArena(arena_pool.ArenaMap)` adds the GL buffer: `adopt` (move a
model in from another arena, GPU to GPU), `compact` / `trim` (copy everything, packed down, into a fresh buffer and drop the old
one; a copy inside one buffer may not overlap itself), `destroy`; a subclass sets `STRIDE_BYTES` (bytes per slot) and may use
`_buffer_replaced()` to point something else (a texture buffer) at the new buffer. `ArenaPoolBase` is the mechanics of a pool,
which is a class with class-level state that mixes it in: `_request_maintenance` asks `app.CallLater` for ONE pass per burst of
changes (`_maintenance_pending` is set when `CallLater` is called and cleared in a `finally` when the pass ends; from another
thread it bounces through `app.CallAfter`), `_run_maintenance` takes `owner.editor3d.context` (`set_owner(mainframe)`, one owner for
all pools) and runs `_maintain` (plan with `arena_pool.plan`, replay with `_execute`), failures are logged and leave `_dirty` set.
A pool fills in the hooks `_pool_arenas`, `_compact_threshold`, `_compact_min_free`, `_long_capacity`, `_short_capacity`,
`_desired_tiers`, `_make_arena`, `_executed` and optionally `_log_pass`. Users: `vbo.PooledVBOHandler` and `wire_pool.WirePool`.

#### arena_pool.py

GL-free bookkeeping and planning for the pooled model arenas of `vbo.py` (new 2026-11-08). `ArenaMap` is the free list of one
arena (allocations, free ranges, fragmentation, `slide()`, `clone()`), with a `tier` (`TIER_SHORT` / `TIER_LONG`), a `locked`
flag and a `uid`; `vbo.py`'s `_MeshArena` subclasses it and adds the buffer. `plan(arenas, desired, long_capacity,
short_capacity, threshold, min_free_vertices)` works on copies and returns the list of `ArenaOp` steps (`create` / `slide` /
`move` / `lock` / `trim` / `delete`) that put every model in the tier its user count asks for, pack the arenas into as few as
possible (a model goes into the arena that is left with the least free space; an arena whose models all fit in the others of
its tier is drained and deleted), lock a long arena that cannot take a model moving to the long tier and trim it to what it
uses, and slide the fragmented ones. It never touches its input and a second plan on its own result is empty. No GL, so it can
be tried in plain Python; `vbo.py`'s `PooledVBOHandler._execute` replays the steps on real buffers.

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

`ContextManager` / `CONTEXTS` (the module singleton) is the one place that tracks which GL context is
current on a thread. `GLContext._acquire`/`_release` just call `CONTEXTS.enter(self)`/`.exit(self)`. An
enter that has to switch contexts pushes a frame holding the context that was current (a canvas's
`GLContext`, found through the `QOpenGLContext` -> canvas registry, or any other context such as an
offscreen one); the matching exit makes THAT context current again (a canvas's own `makeCurrent()`, so
its framebuffer is bound too), and calls `doneCurrent()` only when nothing was current before. An enter
that finds its own context already current (inside that canvas's `paintGL`) switches and restores
nothing. The stack is per thread. RULE: nothing may call `makeCurrent()`/`doneCurrent()` on a canvas
directly to work in another canvas's context while a paint may be running -- go through
`with canvas.context:`. The rule exists because the arena maintenance pass (`arena_buffer.py`, runs
under `editor3d.context`) could run while another canvas was painting and its `doneCurrent()` left the
paint with no context: every GL call failed with `GL_INVALID_OPERATION` and Qt finished the paint with
an access violation. Not covered: the raw `QOpenGLContext` code in `app.py`, `gl/info.py` and
`ray_tracing/renderer.py` (start-up / offscreen, never inside a paint).

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
through `object_picker` exclusively. `_render_id_of` (the tie-break between overlapping floating panels) returns the render id of a peg-board wire table AND of a concentric section widget (`is_pegboard_table` / `is_pegboard_section`); both draw from `Table._render_id_counter`.

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
an `_update_position` override (see `Rings3D`/`Arrows3D`). `_MeshArena` (an `arena_buffer.BufferArena`: an `arena_pool.ArenaMap` plus a GL buffer) is a GPU buffer that models are sub-allocated from; it
compacts, trims and hands models to another arena by GPU-to-GPU copies (`_gpu_copy`, no CPU round-trip). There are many
arenas, in two tiers (user design, 2026-11-08): short-term (models with fewer than `MODEL_TIER_LONG_REFS` = 2 users,
half the size of a long one, never trimmed) and long-term (two or more users; one open arena at a time, locked when a
model moving to the long tier does not fit and then trimmed to the space it uses). A new model always starts in a short
arena. `PooledVBOHandler.ref_count` (`vbo.ref_count += 1` / `-= 1`, main thread only; `Base3D._set_model` / `_delete`
do it) decides the tier; crossing the boundary, freeing a model, resizing one, or a locked arena with free space asks
for a maintenance pass with `app.CallLater` (`_request_maintenance`; the flag `_maintenance_pending` is set when
`CallLater` is called and cleared in a `finally` when the pass ends, and while it is set nothing else is asked for).
The pass (`_run_maintenance` -> `_maintain` -> `arena_pool.plan` -> `_execute`) takes `owner.editor3d.context`
(`PooledVBOHandler.set_owner(mainframe)`, called once in `MainFrame.__init__`; the pool imports no canvas module),
moves models, repoints each moved handler's `_model_arena`, clears the VAOs that held old offsets, and `glFlush`es so the
other canvases see the copies. A failing pass is logged, not raised, and leaves `_tier_dirty` set for the next trigger.
The on-demand compaction in `_allocate_model_arena` (when a new model fits no short arena) is kept as the fallback. ⚠ The
canvases' contexts are ONE share group (`app.py` sets `AA_ShareOpenGLContexts`): buffers and textures are shared, VAOs,
FBOs and queries are not, which is why a handler keeps one VAO per context and `_clear_vaos` deletes only the current
context's (deleting another context's id would delete an unrelated VAO of this one). The scheduling and the replay of a plan are
`arena_buffer.ArenaPoolBase`'s (shared with the wire pool); `PooledVBOHandler` fills in its hooks.
`PooledVBOHandler` is a per-model-id refcounted singleton (`VBOSingleton` metaclass +
`acquire()`/`release()` — a different, unrelated pair from `GLContext`'s, deliberately kept as a
manual acquire/release) so every object sharing a model reuses the same uploaded GPU data;
`NonPooledVBOHandler` extends `VBOHandlerBase.render()` via `super()` for private, non-shared
single-buffer meshes (e.g. decals, gizmo geometry).

#### floor_outline.py

(NEW 2026-11-08) The outline a selected wire, bundle or cable casts on the floor, `WAYPOINT_REWORK_DESIGN.md`. `silhouette_loops(chords, radius)` traces the path seen from above (runs of the drawn chords, left side out and right side back, mitred corners capped at 3 radii, a vertical piece dropped, a circle for a path that is vertical throughout); `outline_vertices(loops, width, y)` makes thin flat strips lying on the floor, both faces; `FLOOR_OUTLINE.draw(program, material, vertices)` draws them through the faces program from its own interleaved buffer (position, smooth normal, face normal; one buffer, a vertex array per context). Everything but the draw is numpy. Checked offscreen from above.

#### wire_batch.py

All the wires, cables and bundles of a frame in ONE draw call (new 2026-11-08, `TWISTED_WIRE_DESIGN.md`; always on since the same day: the `batched_wires` switch and every older way of drawing a wire are gone). A canvas calls `BATCH.begin()` when it starts
drawing its objects (`CanvasBase._draw_scene`), each wire, cable and bundle hands in an ENTRY per conductor (`BATCH.add(texture, entry,
vertices)`, so the draw loop does a list append per conductor), and `BATCH.flush(program)` draws everything collected with one
`glDrawArrays` per pool arena (normally one). An entry is 10 RGBA32F texels: the wire's first row in the pool and its row count, the
entry's first vertex in the draw (filled in by `flush`), the stripe half angle, the twist rate and the conductor's circle, the
material's ambient / diffuse / specular / shininess / emissive, the stripe's three colours, and (texel 9) the vertex within the wire's own draw where the entry's rows begin (0 unless the entry is only part of a wire: a bare conductor end). `make_entry` / `entries_for` build them
from `GLMaterial`s and the pool's `locate`; a wire keeps its entries until `WirePool.stamp(key)`, its look or its selection changes.
`faces/vertex.vert` (`twistBatch`) finds the entry of its vertex by a binary search, then its piece in the wire's rows, and
`faces/fragment.frag` reads the material from the same texels through the flat varying `fragEntry` (-1 for everything else), so a
wire's colour, stripe and size are data and a frame costs one draw whatever the number of wires or how they are coloured. The canvas
flushes twice: after the main object loop (every wire that is not the selected object; they are opaque, so where in the loop each was
drawn made no difference) and once more at the end for a selected wire, which is drawn after the loop as before. There is no
fallback: an object that hands itself in outside a canvas's `_draw_scene` is simply not drawn. **2026-11-08:** `entries_for` skips a span with no pieces: a wire of ONE piece that is bare at an end (`TubeMixin._bare_ends` gives (1, 0)) had an empty middle span whose first piece was not a row of the wire (`IndexError` every frame, in the log as `object render error`).

#### wire_pool.py

The pool of wire path rows (new 2026-11-08, `TWISTED_WIRE_DESIGN.md`): the GPU holds every wire's path and a wire is drawn with ONE
call per conductor (it was one per path piece, ~17 uniforms each: 0.85 ms of CPU per wire per frame). A piece is a row of 5 RGBA32F
texels in a texture buffer (position + length, quaternion, phase + ring count + the piece's first vertex within the wire as int
bits, two mitres); `faces/vertex.vert`'s batched mode finds its piece by a binary search on the first-vertex values, which are
relative to the wire, so a wire's rows mean the same wherever they sit and move by plain copies (no global prefix array to
rebuild). `WirePool` (class-level, an `arena_buffer.ArenaPoolBase`; `WireArena` is a `BufferArena` plus the texture, re-pointed
when the buffer is rebuilt): `pack(...)` makes the rows from `twisted_path.build_path`'s arrays, `set_rows(key, rows, vertices)`
writes them (in place when the piece count is unchanged, otherwise re-allocated and a pass asked for), `release(key)` is
bookkeeping only (the wire calls it from a `weakref.finalize`), `locate(key)` gives the draw its texture / first row / row count /
vertices. No tiers: every wire arena compacts and drains, none is locked or trimmed. `WIRE_ARENA_ROWS` (100,000 since 2026-11-08, 8 MB, so a frame's wires are normally all in one arena) sizes a
new arena (capped by `GL_MAX_TEXTURE_BUFFER_SIZE`). The pool's texture unit is `POOL_TEXTURE_UNIT` (4). Always on since 2026-11-08 (the
`pooled_wires` switch is gone); `objects/mixins/tube.py` is the user. `WirePool.stamp(key)` changes whenever a wire's place in the pool or the vertex count of its draw does (written to a new place, resized, an arena rebuilt under it by a compaction); whatever is derived from `locate` (the batch's entries) is good while the stamp is unchanged.

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
landed, renamed form of what `harness_designer/gl/canvas_base/MAP.md` DESIGN NOTES's "`gl/new_canvas_base` — the shared base class, started
(2026-08-12)" entry describes as just-starting scaffolding — on-disk evidence (directory names,
and a stray "`new_canvas2d` is dedicated to the flat schematic/pegboard views" comment still
sitting inside current `camera_base.py`) confirms the rename (`new_canvas_base`→`canvas_base`,
`new_canvas2d`→`canvas_schematic`, with `canvas_pegboard` kept as its own sibling rather than
merged into one combined 2D package) has fully landed; that `harness_designer/ui/editor_pegboard/MAP.md` DESIGN NOTES entry (and the sibling
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
out from under `gl/canvas_3d/` (superseding the old `canvas3d/culling.pyx` location `harness_designer/gl/culling/MAP.md` DESIGN NOTES's
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

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### GLContext is `with`-only: manual acquire()/release() removed (2026-07-29)
`gl/canvas_base`'s `GLContext` (the re-entrant, thread-safe wrapper around a `QOpenGLWidget`'s `makeCurrent()`/`doneCurrent()`) has no public `acquire()`/`release()`; they are private `_acquire()`/`_release()` used only by `__enter__`/`__exit__`. Always `with some_widget.context: <GL work>` (re-entrant, safe across early returns and exceptions). Why: call sites used to do `ctx.acquire(); <GL work>; ctx.release()` with no `try/finally`; Qt silently swallows an exception raised in a slot or callback, so `release()` was skipped and `GLContext.ref` leaked upward permanently. Every later `acquire()` then saw `ref != 0`, trusted "already current" and skipped the real `makeCurrent()`, surfacing as random `RuntimeError: context has not been acquired` or "Cannot make QOpenGLContext current in a different thread" crashes at unrelated moments (model downloads, app close). Catching at each call site would not fix it; only `with`/`__exit__` guarantees cleanup. VBO handlers' own `.acquire()`/`.release()` on `PooledVBOHandler`/`NonPooledVBOHandler` are NOT `GLContext` and were left alone. For any acquire/work/release pattern where an exception between the steps leaves shared state wrong, prefer a context manager.

#### `gl/*/__init__.py` TODO audit comments go stale fast
The `canvas_3d`, `canvas_schematic` and `canvas_pegboard` `__init__.py` files carry a hand-maintained "TODO: re-audit (Nth pass)" bullet list. In the 2026-08-17 pass roughly half the bullets were already fixed or inaccurate (the files had been renamed and restructured). Verify each bullet against the current source (grep the symbol, read the code) before presenting or "fixing" it. Remove a stale bullet; when a fix is applied, replace the bullet with a short "FIXED: ..." note to keep the audit trail (the user has consistently approved both).

#### Legacy fixed-function immediate-mode GL calls silently render nothing under the shader pipeline (2026-08-21)
Code that draws with `glUseProgram(0)` + `glEnableClientState(GL_VERTEX_ARRAY)` + `glVertexPointer` + `glColor4f` produces no pixels once objects render through the VAO + shader pipeline (`faces_program`/`edges_program`/`vertices_program`): the left-over bound VAO does not mix with client-side arrays (probably `GL_INVALID_OPERATION`, unseen because nothing checks `glGetError()`). The cavity overlay hit this (the pick logic worked, only the draw no-opped). Search for those four calls together. Rebuild such geometry as a small `NonPooledVBOHandler` (packed layout: positions, smooth normals, face normals, each `count*3` floats; `.update(data, count)` re-uploads into the same buffer for a per-frame decal) and draw through the faces/edges program the real geometry uses, with an identity object transform if the positions are world-space. Reference: `Housing3D._draw_overlay_faces`, which threads `faces_program` through `render_surface_overlay`/`render_marker_overlay`/`_render_cavity_markers`/`_render_terminal_overlays`/`Terminal.render_cavity_overlay`. Gotcha: `color.Color(r, g, b, a)` treats a FLOAT channel as 0.0-1.0 (x255 internally) and an INT channel as 0-255, so pass raw 0.0-1.0 floats (`Color(*color)`), never pre-multiplied. `ui/dialogs/housing_editor/housing_editor.py`'s `SurfaceOverlay` sidesteps the trap with a `QPainter` screen-space overlay.
