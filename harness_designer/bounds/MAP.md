## FILES

#### __init__.py

Package marker for `bounds/`; no logic of its own. The package as a whole is pooled bounding-box
/ wire-path storage — one set of fixed-size numpy-backed pools per view (3D, schematic, pegboard),
held by a single `Manager` — the backing store that picking (ray/hit-testing), frustum culling, and
the wire router's wire-to-wire spacing checks all read from directly, rather than each object
owning its own bounds state.

#### aabb.py

`AABB(ArrayPool)` — the axis-aligned box pool. `extent()` returns the pool-wide min/max corner
pair, used for "fit camera to project" bounds.

#### array_pool.py

`ArrayPool`, the generic block/slot engine behind both the AABB and OBB pools: fixed-size numpy
blocks (`_add_block`) so a row's memory address never moves once allocated (`allocate`/`release`
manage a free-list for reuse), a per-slot weak ref back to the owning object (`resolve`), visible
flags (`mark_visible`/`reset_visible`/`is_visible`) and category tags (`set_tag`/`rows_tagged`,
e.g. `TAG_OBSTACLE`) for fast "all obstacles" queries. `hit_test(origin, direc, t0, t1,
visible_only=True)` is the vectorized ray test every picker goes through, and `_vectorized_ray_test`
is the shape-specific (AABB vs OBB) ray math each subclass overrides. **The per-frame
`mark_visible` call is the real pickability gate, not registration or culling** — `hit_test`'s
default `visible_only=True` means only a slot marked visible *this frame* is a ray-test candidate,
and `BaseVar.render()` only calls `mark_visible` after its `if not self.is_visible: return`
early-exit, so an object that never draws by design (e.g. a probe) is invisible to every picker
unless something else explicitly marks its slot visible. This produced a real regression
(2026-10-08): the pooled-bounds picking refactor (`cb1d9cc`/`20aa1bb`, 2026-09-19) silently broke
every invisible wire-snap probe in `wire_snap`/`snap_probe_set`/`pseudo_wire_layout`, fixed via a
`db_obj.is_snap_probe` flag that `BaseVar.render()` checks (try/except `AttributeError`) to call
`mark_visible` without drawing — see MEMORY.md's "Wire-snap feature" entry for the full incident
writeup; any new kind of invisible-but-pickable object needs the same flag, not just a registered
OBB/AABB slot. Frustum culling (`gl.culling.cull`) and bounds-pool registration both happen
unconditionally regardless of `is_visible3d`; only the per-frame `mark_visible` call is gated on
it, so neither culling nor registration state tells you anything about pickability on its own.

#### manager.py

`Manager`, with one `View` per editor (`editor_3d`/`editor_schematic`/`editor_pegboard`), each
`View` exposing its own `.aabb`/`.obb`/`.segments` pool instance. `Manager.reset()`/`View.reset()`
drop storage in place without recreating the pool objects themselves, specifically so canvases
holding long-lived references to a `View`/pool don't go stale across a project unload/reload — but
an object with a live slot index across a reset (e.g. a `FocalTarget` that isn't torn down via
`ObjectBase.delete()`) will hit `IndexError` in `mark_visible`, which is why `FocalTarget` is
explicitly deleted/recreated around every `Manager.reset()` call rather than just surviving it (see
MEMORY.md's "Stored project bounds + fit-to-project camera" entry). Project-level bounds storage
(`projects.bounds_3d`/`bounds_schematic`/`bounds_pegboard`, read at project load / written at
unload via `View.aabb.extent()`) is a separate, DB-persisted concept from the live in-memory pools
here — see that same MEMORY.md section for the load/unload ordering and the camera-fitting half,
which lives in `gl/`, not here.

#### obb.py

`OBB(ArrayPool)` — the oriented box pool, same `ArrayPool` machinery as `aabb.py` but with its own
rotated-box ray test.

#### segment_pool.py

`SegmentPool` — wire paths stored as a deduped, refcounted vertex list (each `Point.as_numpy`
buffer referenced live, so a point moving updates every segment that uses it with no copy) plus
per-wire index pairs. `segments(exclude, window)` returns every wire's segments as one array —
this is what the router's wire-to-wire lane/spacing check (`wire_routing/routing.py`) reads,
registered by `objects/objects_schematic/wire.py`. `register`/`release`/`_acquire`/`_drop` manage
slot lifetime; `_on_dead` is the weakref cleanup callback for a garbage-collected owner.
