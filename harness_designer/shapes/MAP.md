## FILES

#### __init__.py

`cache_primitives(mainframe, splash=None)` — the startup warm-up pass that pre-generates/caches
every primitive's mesh (and, via `text.build_chars`, every glyph), with progress callbacks
(`_on_glyph_progress`) feeding a splash screen. The package as a whole holds procedural geometry
generators ported from a small C 3D library — deliberately NOT build123d, because direct mesh
generation is far faster for primitives than going through a CAD kernel. Most files here follow
one shared pattern: a module-level `create(...)` returning raw `(vertices, normals)` numpy
arrays, and a `create_vbo()` wrapping that into a pooled VBO handler for GL rendering. Five files
in this directory (`square_outline.py`, `disc_ring.py`, `triangle.py`, `text.py`, `mesh_cache.py`)
are not mentioned in CODEBASE_MAP.md's flat `shapes/` file list, which is stale — see each file's
own entry below.

#### arrow.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### box.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### circle.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### cone.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### cylinder.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### cylinder_helix.py

A composite generator built from `build123d` shapes (`_stripe_profile`, `_straight_stripe`,
`_loop_stripe_guide`, `_loop_stripe`) rather than the hand-rolled vertex/normal math the other
primitives use — produces a cylinder with a helical stripe pattern (e.g. for striped wire
rendering). Exposes both `create_vbo()` (the base cylinder) and `create_stripe_vbo()` (the stripe
geometry) as separate VBOs. This is a build123d usage *within* `shapes/`, alongside `text.py`:
`shapes/` is "deliberately NOT build123d" as a rule, but that rule is specifically about
*primitive* mesh generation (box, sphere, cylinder, etc. are hand-ported from a C library because
build123d is overkill/slow for them) — striped-cylinder geometry is the kind of problem build123d
is actually suited for, so don't treat this as drift from the rule.

#### disc_ring.py

An outline/ring-variant (non-solid) primitive generator exposing `create(...)`/`create_vbo()`.
Not listed in CODEBASE_MAP.md's `shapes/` file list (stale). Its `create_vbo` returns a
`NonPooledVBOHandler`, breaking the `PooledVBOHandler` pattern every other primitive in this
package uses — noted but not investigated further; if extending it or copying its structure for a
new shape, check whether that's because disc/ring instances are inherently non-poolable (e.g.
per-instance dimensions too varied to pool) before assuming it's an oversight. `PJTWireServiceLoop.length_mm` is worked out from this module's loop numbers (the helix's radius, pitch and height and the two straight pieces in `create_vbo`): change one and change `length_mm` in `database/project_db/pjt_wire_service_loop.py` with it (it has no constants of its own: it works the helix out from the wire diameter, and adds the two tails as `diameter * 2.0`).

#### helix.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### line.py

**Not a procedural mesh generator**, and not listed correctly by CODEBASE_MAP.md's flat
`shapes/` listing, which groups it alongside the procedural primitives ("box / sphere / cylinder /
cone / torus / helix / cylinder_helix / arrow / circle / rectangle / line") as if it followed the
same `create()`/`create_vbo()` pattern — it does not. This is a stateful `Line` class for 2D
plot/schematic rendering (`add_to_plot(axes)` takes an `Editor2D`), backed by a Qt `QPixmap`
texture (`_get_pixmap`/`_make_qcolor`) rather than a VBO, with `p1`/`p2`/`width`/`color`/
`stripe_color` properties bound to `geometry.point.Point`/a `Color` type. It is architecturally
unrelated to every other file in this directory and distinct from `geometry/line.py`'s own `Line`
class (a pure numeric two-point segment) — **flag this prominently and never use it as a template
for a new primitive shape**, and don't confuse the two `Line` classes when both are in scope.

#### mesh_cache.py

On-disk cache for generated primitive mesh data — `path(name)`, `load(name, version)`,
`save(name, version, packed, count, aabb, obb, extra=None)`. Versioned by an explicit `version`
int per cached mesh, so a primitive's generation code can bump its own cache format independently
of others. Not listed in CODEBASE_MAP.md's `shapes/` file list (stale) despite being substantial
enough (a full mesh disk-cache) to warrant its own bullet there.

#### rectangle.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern, plus additional `create_based`/
`create_vbo_based` variants.

#### sphere.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### square_outline.py

An outline-variant (non-solid) primitive generator exposing `create(...)`/`create_vbo()`. Not
listed in CODEBASE_MAP.md's `shapes/` file list (stale).

#### text.py

3D text/label geometry — tessellates real font glyphs via `build123d` (`_tessellate_char`,
`build123d.FontStyle`) into cached per-glyph VBOs (`_glyph_cache_path`/`_load_glyph_cache`/
`_save_glyph_cache`, `_build_char`, `build_chars` for a full warm-up pass), assembled into
words/lines by the `Text` class (`_layout`, `_add_word`, `build_vbos`). Also owns
`_CameraTrackingArena`/`update_camera_tracking` — a billboard-style registry
(`_billboard_matrices`) for text that must always face the camera, with its own growable capacity
arena (`_grow`) separate from `bounds/`'s `ArrayPool`. `geometry/cavity_layout.py` depends on this
file's `Text`/`CHARACTER_HEIGHT`/`TOP_DOWN_TILT` for cavity-number engraving layout — a deliberate,
legitimate exception to the "`shapes/` is NOT build123d" rule (real font-glyph tessellation is
exactly the kind of problem build123d is suited for), not a violation of it. Not listed in
CODEBASE_MAP.md's `shapes/` file list (stale).

#### torus.py

Procedural primitive generator exposing `create(...)` (raw mesh data) and `create_vbo()` (pooled
VBO), following this package's shared generator pattern.

#### triangle.py

Procedural primitive generator exposing `create(...)`/`create_vbo()`, parameterized by side
lengths/angles (`side_a`/`side_b`/`side_c`/`angle_A`/`angle_B`/`angle_C`) rather than fixed
dimensions, unlike its siblings. Its `create_vbo` additionally takes a `uuid` parameter that none
of the other `create_vbo()` functions in this package take (likely a per-shape cache/identity key
distinguishing differently-shaped triangle instances, given triangles are fully
dimension-parameterized rather than fixed-shape) — confirm its purpose with `dep_trace.py --calls
--name create_vbo` before relying on it. Not listed in CODEBASE_MAP.md's `shapes/` file list
(stale).
