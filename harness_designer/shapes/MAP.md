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
of others. Each cache is one `<appdata>/<name>.hdm` file (the format is in `utils/hdm.py`; a
`<name>.npz` written before it is upgraded in place the first time it is loaded). Not listed in
CODEBASE_MAP.md's `shapes/` file list (stale) despite being substantial
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
`_save_glyph_cache`, `_build_char`, `build_chars` for a full warm-up pass; every glyph is in the one
`glyph_cache.hdm` file, see `utils/hdm.py`), assembled into
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

#### twisted_path.pyi

Type stub of `twisted_path.pyx`: the signature and return shape of `build_path`.

#### twisted_path.pyx

Hand-written Cython (registered in `builder/cython_build.py`'s `_HAND_WRITTEN_EXTENSIONS`; the `.pyd` is gitignored, build it with the steps in MEMORY.md's "Cython extensions (.pyx)") -- the path building behind `objects_3d/wire.py`'s `_twist_segments`. `build_path(starts, rotations, quats, lengths, joined, bend_radius, rounded, rate, outer_radius, start_phase, bend_step, samples_per_turn, max_rings)` takes a wire's straight segments as float64 arrays and returns, for every piece that is drawn, its position, quaternion, rotation matrix, length, twist phase, the two mitres, the ring count and the input segment it is cut from. It is `twisted_wire.round_bends` + the frame of each chord + `plan` + `ring_count` in one call with no Python object per piece. A chord's frame is the minimal rotation from +Z to its direction (equal to `Wire._rotation_from_direction` to about 1e-7); a piece cut from an input segment keeps that segment's own rotation, so a ribbon's roll survives. The old route made a `Point` and an `Angle` (Decimal-backed) for every chord, which was 69 percent of an 8.1 ms rebuild of a 22-piece wire; `build_path` takes about 0.016 ms for the same wire. The pure-Python `round_bends` / `plan` / `ring_count` in `twisted_wire.py` are its reference, not a fallback: `build_path` was checked against them over 20,000 random bent paths (276,000 pieces, 2026-11-07) with every output equal, and `plan` / `rolled` are still what the ribbon code calls. The epsilons (`_U_TURN`, `_ROUND_MIN`, `_STRAIGHT`) are copies of `twisted_wire`'s and the tunables are passed in: change the maths in one place and change the other with it.

#### twisted_wire.py

**Any conductor count (2026-11-05):** `profile` packs 2 to any number of equal conductors (ring up to 5; from 6, conductor 0 in the centre and the rest around it on a ring up to 9, else in stranded layers). **Lay length is clamped (2026-11-05):** `rate_for(tpi, outer_diameter)` is the rate a cable is drawn with (`Wire._build_twist` calls it, not `rate_from_tpi`): the lay length is never shorter than `MIN_LAY_DIAMETERS` (8) cable diameters. The catalogue gives most pairs a flat TPI of 1.0 whatever their size, so a thick pair (the 6.3 mm 12 AWG M27500 pair is 4 diameters per turn) was drawn as a steep, swollen, pinched helix; thin pairs are 12+ diameters per turn at 1 TPI and are unchanged. NOT a mesh generator (NEW 2026-11-05): the maths and the draw call of a twisted pair / triple (`TWISTED_WIRE_DESIGN.md` sections 5 and 7). `profile(count, outer_diameter)` gives each conductor's circle in the cable's cross-section; `plan(rotations, lengths, joined, rate, outer_radius)` works out, for the segments of a bent wire, the twist phase carried across each joint (parallel transport) and the mitre that closes the outside of the bend; `ring_count` sizes a segment's tube. There is no draw call here any more: `TwistedTube` (`TUBE.draw`, `TUBE.draw_pooled`) was removed 2026-11-08 with the per-piece and per-wire draws; `gl/wire_batch.py` draws every tube of a frame with one call and `gl/shaders/faces/vertex.vert` makes every vertex from `gl_VertexID`. `SIDES` must equal `TWIST_SIDES` in that shader. Checked 2026-11-05 with throwaway scripts (offscreen GL render through the real `FacesProgram`, and a numeric copy of the shader maths over 2000 random bends of 5-150 degrees: the end ring of a segment and the start ring of the next agree to 1e-13 mm); the app itself was not run. **Ribbon / jacketed (2026-11-06, step 4):** `ribbon_pitch` / `insulated_diameter` (the catalogue gives no pitch: the smallest of `RIBBON_PITCHES` that holds the bare conductor plus `INSULATION_MM`), `ribbon_profile(count, pitch)` (a row of touching circles across X, pin 1 at -X, the web not drawn), `jacket_diameter(count, insulated)` (the diameter that holds the conductors, for a jacketed part with no `od_mm`) and `rolled(rotation, phase)`; `plan` takes a `start_phase` (the ribbon's roll; rate 0). A ribbon goes through the same shader as a twisted pair with rate 0. Checked offscreen (straight and bent, 12 conductors). **Rounded bends (2026-11-07):** `round_bends(starts, directions, lengths, joined, radius)` replaces each corner between joined segments with a tangent arc drawn as chords of `BEND_STEP` (10 degrees) at a radius of `BEND_RADIUS_DIAMETERS` (1 since 2026-11-07, was 4) diameters of the wire or of the whole cable (never of one conductor in it), cutting the neighbouring segments back (a corner takes at most half of each of its two segments, so on short segments the arc is tighter; a U-turn and a corner at a break in the chain stay corners). It returns `BendPiece`s (`source` = the input segment a straight piece is cut from, -1 for a chord) that `plan` then takes in place of the raw segments, so the mitre only ever closes a gap of at most 10 degrees (3 mm fade for a raw 90 degree corner at 3 mm OD, 0.26 mm rounded). Applies to every look but a ribbon's (`_TwistLook.rounded`): a twisted cable, and a single wire drawn through the twist mode; a ribbon is not rounded. The rounding is done by `twisted_path.build_path` now. 
