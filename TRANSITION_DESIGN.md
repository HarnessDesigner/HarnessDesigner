# Transition design

Single home for everything transition-specific: how the transition model is
built and rendered, what has been decided, what the code currently does, and
what is left to do to move the real app off `build123d`/OCC and onto GPU
primitives. Add to this file as the design firms up; do not scatter
transition design into MEMORY.md (which only keeps a pointer here).

Everything below the catalog/DB layer was worked out and prototyped in
`scratches/transition_viewer/` (gitignored, throwaway), then ported into
the real app -- see section 7's per-step status. The scratch tool itself
has done its job (validating the design, then fixing all of section 6's
catalog data problems) and is not being extended further.

Last updated: 2026-09-27 (section 7 ported into the real app; see
`TRANSITION_EDITOR_DIALOG.md` for the in-app dialog built on top of it).

Sections:
1. Scope
2. Where things stand today (the OCC pipeline, and why it's being replaced)
3. Data semantics (decided, confirmed against real behavior)
4. The primitive design (decided)
5. Performance
6. Known catalog data problems (not a code issue)
7. Implementation order (porting the scratch into the real app)
8. Future: user-authored transitions/boots/etc. via a 3D dialog
9. Open questions
10. Decision log

---

## 1. Scope

A transition is a catalog part with 1-6 branches (`branch_count`,
`branches`/`transition_branches` in the global DB) that a bundle's ends
attach to. This file covers how a transition's own 3D **model** is built and
rendered -- placement, cross-view behavior, attaching bundles to branches,
and the skeleton (bundle/transition graph) all belong in
`BUNDLE_PLACEMENT.md` instead. `objects/objects_3d/transition.py`,
`objects/objects_pegboard/transition.py`, `database/global_db/transition.py`
and `database/global_db/transition_branch.py` are the real files this will
eventually change; nothing there has been touched yet except the two
migrations in section 3.

## 2. Where things stand today (the OCC pipeline, and why it's being replaced)

`objects/objects_3d/transition.py`'s `_build_model()` builds a transition's
mesh with `build123d`: each branch is an OCC `Circle` extruded along its own
axis, with an optional wider "bulb" cylinder and one or two capping spheres
near the root, and every piece is unioned into one boolean solid
(`model += piece`). `utils/model_utils.convert_model_to_mesh()` then
triangulates that solid with OCCT's incremental mesher.

A live audit of the real catalog (built every one of the 111 transitions,
comparing against the actual `harness_designer.db`) found this pipeline is
fragile in ways the boolean CSG approach cannot avoid:

- **9 parts have no geometry at all** (`branch_length`/`angle` all zero) --
  a catalog data problem, unrelated to the pipeline; see section 6.
- **1 part (`462A214-25/225-0`) returns a `ShapeList` instead of a solid.**
  Two of its branches sit at the same angle, offset sideways by exactly the
  sum of their bulb radii -- their bulb cylinders are exactly tangent, and
  OCC's fuse leaves them as separate, untouching solids. The app would
  crash here (`ShapeList` has no `.wrapped`).
- **10 parts build a `Solid` but fail `is_valid`.** Re-testing at both min
  and max branch diameter showed several parts flip valid/invalid depending
  on which diameter is chosen -- i.e. the fuse is running right at a
  fragile near-tangency for ordinary catalog dimensions, not just
  degenerate ones. All rendered as plausible, undistorted solids by eye at
  every diameter tested (no visible gaps or self-intersections) -- the
  fragility is internal to OCC's boolean classification, not something a
  user would necessarily see.
- **5 parts (`362A024-25-0`/`225`/`86`, `362A114-25-0`/`225`) render a
  valid but visibly wrong solid** -- a full-size sphere balloons right at
  the transition's own vertex, dwarfing everything else. Root cause: a
  stray `bulb_offset = [-0.1, 0, 0]` on a non-trunk branch. The model
  code's "does this branch have a `bulb_offset`" special case was only
  ever exercised by the trunk in every other part in the catalog; a
  near-zero offset on any other branch plants the near-vertex sphere from
  that case almost exactly at the vertex, full size. See section 6.
- **Boolean seams are visible even on parts that build a valid solid.**
  Every boolean fuse cuts new faces at each intersection curve, and each
  trimmed face is triangulated independently -- vertices along a shared
  trim boundary between two different faces essentially never land at
  exactly the same position, so the model's own smooth-normal averaging
  (`utils/mesh_normals.compute_normals`, which blends by shared vertex
  position) cannot blend across that boundary. The result is a visible
  lighting discontinuity at every boolean seam, on an otherwise
  mathematically smooth surface.
- **It's slow relative to the alternative below**, and worse, the cost is
  paid on every edit: `Transition.build()` reruns the entire OCC pipeline
  (boolean fuse + OCCT triangulation) from scratch on every single
  diameter/position change.

None of this is a bug in any one part's data (aside from section 6) --
it's what boolean CSG costs structurally, and it doesn't get better by
fixing individual rows.

## 3. Data semantics (decided, confirmed against real behavior)

Two migrations were applied directly to the global DB
(`~/AppData/Roaming/HarnessDesigner/harness_designer.db`), in place, with a
`.bak_before_*` backup taken and verified before each:

- `transition_branches.offset`: was `TEXT NULL "[x, y]"` (a single float
  angle's era), is now `TEXT NOT NULL "[x, y, z]"`. NULL became
  `[0.0, 0.0, 0.0]`.
- `transition_branches.angle`: was `REAL NULL` (a single float, degrees),
  is now `TEXT NOT NULL "[x, y, z]"` euler degrees -- **euler is the
  permanent, final storage format here, not a stopgap on the way to
  quaternions.** Gimbal lock is a problem only when *decomposing* an
  arbitrary rotation (matrix/quaternion) back into euler angles; it does
  not occur going the other way, constructing a rotation *from* stored
  euler values and using it directly, which is the only thing this code
  ever does (nothing here ever extracts euler angles from anything else).
  So there is no gimbal-lock exposure to design around, and euler is both
  safe and easier to work with than quaternions for this data (user
  decision, 2026-09-27). The old float was confirmed (against
  `_build_model` and `geometry.angle.Angle`) to be a rotation about Z, so
  it became `[0.0, 0.0, old_value]`. NULL became `[0.0, 0.0, 0.0]`.
- `transition_branches.bulb_offset`: was `TEXT NULL "[x, y]"`, is now
  `TEXT NULL "[x, y, z]"` -- stays nullable (NULL means "this branch has
  no bulb offset", a real, meaningful state, not a migration artifact).
  Non-NULL 2-value rows got `z = 0.0`.

`transitions.json` (the catalog seed data) was **not** touched -- it still
holds the old 2-axis/single-float format.
`database/create_database/transition_branches.py` (already edited, in the
app, not the scratch) now converts that old JSON shape into the new one on
load (`_offset_to_text`/`_angle_to_text`), so re-seeding a fresh DB from the
JSON still produces the new column shape.

Confirmed facts about how these fields behave, load-bearing for section 4:

- **`Angle.from_euler(x, y, z)`'s rotation composition is `R = Ry @ Rx @ Rz`**
  (Z applied first, then X, then Y) -- verified to 1e-7 against
  `Angle.as_matrix_numpy` across a range of combined-axis test cases.
- **`Angle` itself must not be used for this math -- it is float32.** Using
  it directly for a branch's rotation was off by ~6e-8 from the exact
  matrix, and that was enough for OCC's fuse to silently drop an angled
  branch's tube from the union (tube, bulb cylinder and end sphere are
  built exactly tangent, and float32 error is enough to break the
  tangency). The primitive builder computes the same `Ry @ Rx @ Rz` matrix
  itself, in float64.
- **`offset` is a literal point in world (hub) coordinates**, not something
  further rotated by the branch's own angle -- confirmed directly:
  `build123d.Plane(origin=..., ...).rotated(angle)` does **not** rotate the
  plane's `origin`, only its axes. `offset` is `[0, 0, 0]` for every branch
  in the catalog except `462A214-25/225-0`'s twin branch (`[-25.4, 0, 0]`),
  which is a second branch sharing the same transition but rooted 25.4mm
  away from the first branch's own root point.
- **`bulb_offset` is likewise a literal world point** -- the bulb's own
  start point, independent of the branch's own rotation, for exactly the
  same confirmed `Plane.rotated()` reason. It is NULL/zero on almost every
  branch in the catalog; where it is set, it is always on the trunk
  (`angle == [0, 0, -180]`) in every *correctly* populated row. It is not a
  generic per-branch parameter with a coherent meaning at an arbitrary
  angle -- see the two-sphere rule in section 4, which is a literal,
  intentional port of the existing (trunk-only) behavior, not a new rule.

## 4. The primitive design (decided)

Replace `_build_model`'s OCC boolean pipeline with plain cylinder/sphere
primitives, placed by straight vector math (position + rotation), left to
overlap with **no boolean operation at all**. Prototyped end to end in
`scratches/transition_viewer/transition_viewer.py`
(`build_model_primitive()`), verified against the OCC pipeline on every one
of the 111 catalog parts (bounds, branch-tip points, and a full statement by
statement audit against `_build_model` -- see the audit note at the end of
this section).

**Why untrimmed overlap is fine:** a depth-tested opaque render of several
overlapping solid primitives is visually indistinguishable from a trimmed
CSG result from any outside viewpoint -- OCC's "trim" only ever matters for
a boolean *solid* (volume, mass properties, further CAD operations), never
for what a viewer sees, since the z-buffer already picks whichever surface
is closest per pixel regardless of what geometry is hidden behind it. This
holds as long as materials stay opaque (no alpha blending) -- true today for
every transition material (`Rubber`/`Plastic`). Nothing here can ever
produce a `ShapeList` or fail `is_valid`, because there is no boolean
operation that can fail, and it also fixes the boolean-seam shading artifact
from section 2 for the same reason (no trimmed faces are ever created, so
there's no seam for smooth-normal blending to fail across).

**Per branch, in order** (mirrors `_build_model` piece for piece):

1. **Main tube.** One cylinder, full `length`, from the branch's own
   `offset`, along the branch's own axis, at `set_dia` (the diameter
   actually chosen for that branch -- falls back to `min_dia` the first
   time, exactly like `_build_model`).
2. **Bulb**, only if `bulb_length` is nonzero:
   - **If `bulb_offset` is set** (nonzero x/y/z): one wide cylinder
     (`max_dia`, `bulb_length`) from `bulb_offset` along the branch's own
     axis; **two** spheres (`max_dia`), one at `bulb_offset` itself, one at
     `(bulb_offset.x - bulb_length, bulb_offset.y, bulb_offset.z)` -- a
     literal, hardcoded X-only port of `_build_model`'s own second sphere,
     only geometrically meaningful for a branch whose real direction is
     -X (the trunk, the only branch this case is ever exercised on in
     correctly-populated catalog data).
   - **Else:** one wide cylinder (`max_dia`, `bulb_length`) from the
     branch's own `offset`; one sphere (`max_dia`) at
     `offset + bulb_length * direction`, capping the far end where the
     bulb necks down to the tube's own diameter.
3. **Branch tip point.** Same rule as `_build_model`: set once, the first
   time (`position == (0, 0, 0)`), or on demand via `update_points=True`
   (matches `_build_model`'s own parameter, used after an edit that must
   force every tip to recompute).

**Hub sphere (the one deliberate departure from `_build_model`):** one
sphere per **distinct `offset` value** found among a transition's branches
(almost always one, at the shared vertex -- twice for a twin-branch
transition like `462A214-25/225-0`), sized to the largest tube/bulb diameter
of whichever branches share that root point.

Why this is needed, and why it's an improvement rather than a cosmetic
add-on: inspecting the actual triangulated mesh of several *working*
catalog parts (`hub_inspect.py`) showed the "closed, rounded joint" every
working part already has is not a deliberate feature of `_build_model` at
all -- it's an accident of several *wide bulb cylinders*, one per branch,
all overlapping through the same vertex point; when several convex surfaces
overlap like that, the visible boundary blends smoothly with no separate
piece needed. A branch with **no bulb of its own** (`bulb_length == 0`,
e.g. `362A024-25-0`'s trunk) contributes nothing there and is only ever
covered by luck, when some *other* branch's bulb happens to be wide enough
to swallow the gap. Making the hub sphere explicit and universal means every
transition gets a closed joint by construction, regardless of which
branches happen to have bulbs, instead of by chance.

**Audit note (2026-09-27):** every statement and every `branch`/`brnch`
attribute read in `_build_model` was compared line by line against
`build_model_primitive`, including a `grep` diff of every attribute
accessed by each (`idx`, `diameter`, `position`, `min_dia`, `max_dia`,
`length`, `bulb_length`, `angle`, `bulb_offset`, `offset` -- identical
sets). One real gap was found and fixed in that pass: `update_points` had
been dropped entirely from `build_model_primitive`'s signature; it is now
present and behaves identically. The `.rotate(Axis((0,0,0),(1,0,0)),
angle[2])` call on the single-sphere case's sphere was confirmed to be a
true no-op (rotating a sphere about an axis through its own center changes
nothing, and it's applied before the sphere is placed) and is correctly
omitted, not a missed piece.

**GPU representation (not yet built, see section 7):** unit-sized meshes
only, generated once and cached (`shapes/cylinder.py`,
`shapes/sphere.py` already exist, already pooled via `create_vbo()` --
`radius 0.5`, `length 1.0`). Per-instance placement is position + `Angle` +
a 3-axis scale, exactly the pattern `objects/objects_3d/transition.py`'s
existing `Branch` class already uses for its own marker sphere
(`scale = Point(diameter, diameter, diameter)`). For a cylinder the
equivalent is `scale = Point(diameter, diameter, length)` -- x/y scale the
unit-diameter circle to the branch's real diameter, z scales the unit
length to the branch's real length. No custom mesh generation anywhere in
the app version; the scratch generates each piece at its exact real size
directly instead (no GPU per-instance transform pipeline in that legacy
immediate-mode viewer), which is numerically equivalent for a plain
axis-aligned diameter/length scale but is not how the real port should work.

## 5. Performance

Measured directly (`cProfile`, `562A011-25-0`, 5 branches, has a trunk
`bulb_offset`, averaged over 30 rebuilds):

| stage | time |
|---|---|
| OCC pipeline (`_build_model` + `convert_model_to_mesh`), whole catalog range | 82-340 ms |
| Primitive pipeline, `build_part` total (incl. `compute_normals`) | 65.0 ms |
| Primitive pipeline, `build_model_primitive` alone | 43.2 ms |
| -- of which, mesh generation (`cylinder.create()`/`sphere.create()`) | 42.4 ms (**98%**) |
| -- of which, everything else (matrix transforms, numpy concat) | 0.6 ms (~1.4%) |

The 98% is pure-Python tessellation (nested loops calling `math.cos`/`sin`
per vertex) inside `shapes/cylinder.py`/`shapes/sphere.py`'s own `create()`
-- unavoidable the way the scratch calls it (a fresh, exact-size mesh built
per piece, every rebuild), but exactly the part `create_vbo()`'s caching
eliminates: that mesh is generated **once, ever, at the unit size**, for the
whole lifetime of the app, and every real instance after that is a cheap
transform, no tessellation. Expected result once ported: on the order of
50-100x faster than the scratch's own primitive path, and roughly 300-500x
faster than the OCC pipeline it replaces -- a rebuild after a live diameter
edit (which today reruns the entire OCC pipeline) would drop from hundreds
of milliseconds to something on the order of microseconds.

## 6. Known catalog data problems -- ALL RESOLVED (2026-09-27)

All catalog data problems found during the OCC-pipeline audit (9 parts with no geometry, one part with a branch-count mismatch, 5 parts with a stray `bulb_offset` on the wrong branch) and one code bug found while porting (`global_db.Transition.branches`'s `res[idx - 1]` off-by-one, which silently fed every by-position consumer the wrong branch) are fixed and confirmed against the live catalog. See the decision log for dates; no action needed here.

## 7. Implementation order (porting the scratch into the real app) -- DONE

All 7 originally-planned porting steps landed. The concrete shape the port settled on was NOT the `TransitionModel`/`VBOHandlerBase` design this section originally tracked step-by-step -- that approach was itself retired one day later per section 8.6 ("no more shared `transition_model.py`"), in favor of `_BranchBody`/`_Hub`/`_Body` classes written directly in each consumer file. Sections 8.6-8.12 are the authoritative description of the resulting architecture; this section's own per-step history is superseded by that and no longer tracked separately. `_build_model`/`build123d`/OCCT imports were fully retired from `objects/objects_3d/transition.py` (later partially reintroduced in a much narrower, bulb-only scope -- section 8.8).

## 8. Future: user-authored transitions/boots/etc. via a 3D dialog

Not started, not scheduled -- recorded here because it directly shapes why
the primitive design (section 4) is the right long-term choice, not just an
internal rendering optimization. The dialog itself has its own file,
`TRANSITION_EDITOR_DIALOG.md` -- add dialog-specific detail there, not here.

**The goal:** a dialog where a user builds a transition (or a boot, or
similar catalog part) themselves, interactively, in a 3D environment, and
the same per-piece description this file already defines -- offset, angle,
length/diameter, which primitive -- becomes that part's stored definition,
the same data `build_model_primitive`-style code reads back to render it at
runtime. There are many real-world manufacturers of transitions, boots and
similar parts; a user-facing authoring tool is a far more scalable way to
grow the catalog than adding each one by hand in code.

**The accuracy bar is explicitly low:** the user's own words -- "their
visual representation doesn't have to be perfect, it just has to be close
in measurements for the sizes and where things connect." This is exactly
what cylinder/sphere primitives are good at (parametric, trivially
user-adjustable size/position/angle, no CAD modeling skill required) and
exactly what OCC/`build123d` is not (precise but requires real CAD
authoring, not something to expose in an end-user dialog). This is a strong
argument for the primitive design independent of the performance/reliability
case in sections 2 and 5 -- it is the only one of the two approaches that
could plausibly be exposed to a user as an authoring tool at all.

**Implication for section 4/7:** whatever per-piece data shape the ported
primitive design settles on (section 7 step 1's per-branch object question)
should be designed with this future authoring dialog in mind -- it needs to
be a shape a user-facing tool can read and write, not just an internal
render-time structure.

## 8.5 Two porting-bug fixes, carried forward into the current design (8.6+)

Two real bugs were found and fixed while first porting the primitive design (in the since-retired `objects/transition_model.py`, see 8.6), and both fixes were explicitly carried over when 8.6 rewrote the design into today's `_BranchBody`/`Branch` classes -- they are current-code facts, not just history:

1. **Hub sphere diameter is `max(set_dia, max_dia)`, not just `set_dia`** -- otherwise too small whenever a branch with a narrow trunk but a wide bulb shares a hub with other branches.
2. **A branch's bulb cylinder direction must use the branch's own rotated direction, never a hardcoded local +X.** `_build_model`'s original OCC code does `Plane(z_dir=(1, 0, 0)).rotated((0, 0, angle))` -- a REAL rotation, not a no-op -- so any branch whose real direction isn't +X (the overwhelming majority of the catalog) needs the actual rotation applied or its bulb cylinder points the wrong way.

**Lesson for future validation of this code**: an AABB/count-level check can pass while individual pieces are still wrong (a missized/misdirected piece can end up entirely inside, or exactly cancel out against, the volume other correct pieces already cover) -- checking the full instance-by-instance geometry, not just aggregate bounds, is what actually catches this class of bug.

## 8.6 Rewritten per the user's own simplification (2026-09-27) -- no more
## shared `transition_model.py`

The `objects.transition_model.TransitionModel` module (section 8.5's own
subject) was **retired entirely** -- the user found it "insanely complex
when it doesn't need to be" and gave a concrete, much simpler reference
design: a transition's body is just the sum of its branches (no separate
"transition body" shape at all, matching `_build_model`'s own structure
exactly), each branch precomputes its own cylinder/sphere placements
once, and `render()` does nothing but read those cached values and call
`vbo.render()` -- no per-frame transform math, no generic instance-list
abstraction.

Rewritten, and placed DIRECTLY in each consumer's own file rather than a
shared module (the user's own explicit preference -- "it is small enough
to place it directly in the transition.py file for the objects3d and also
the objects pegboard"):

- **`objects_3d/transition.py`**: `_BranchBody` (one per branch --
  trunk + optional bulb, ported from `_build_model` exactly, same
  hub-diameter and bulb-cylinder-direction fixes as section 8.5), `_Hub`
  (the shared-root sphere), `_Body` (owns the branch/hub lists, is this
  object's own `self._vbo`).
- **`objects_pegboard/transition.py`**: its OWN independent `_PegBranchBody`/
  `_PegHub`/`_PegBody` -- NOT sharing the 3D view's `_Body` instance (it
  can't any more: `render()` now draws from each piece's own cached WORLD
  attributes rather than the position/angle `BaseVar._render_geometry`
  hands it, so one shared instance could only ever be correctly
  positioned for one view at a time). Every branch is pre-rotated by a
  fixed `_FLATTEN` (-90 degrees about X) transform at construction, baked
  into its own local data once, so the peg-board view renders correctly
  flat with `angle_pegboard` at identity -- "viewed properly right out of
  the gate," replacing the old one-time mutable-seed-rotation hack that
  only ever applied to a freshly-placed row.

**Discipline enforced throughout, per the user's explicit correction**
(an earlier draft of this rewrite still computed everything in
`__init__`, which they caught immediately): a piece's `__init__` stores
ONLY its identity and permanent catalog-defined shape data (offset,
local direction, bulb geometry) -- never an angle, diameter or position.
Separate `update_diameter()`/`update_position()`/`update_angle()` methods
compute and cache everything `render()` needs, called once right after
construction and again any time one of them actually changes; `render()`
itself is a pure cache read with zero computation. "Keep all calculations
out of the render pipeline; cache all values used in the render
pipeline" (user, 2026-09-27) is the rule this whole shape follows.

Also added, per the user's own description of what the `Transition`
class should eventually do: `_BranchBody.hit_test_outer()` (distance-to-
segment against a branch's own outer 20% -- the mouth, for "drop a
bundle/wire on this branch" interactions) and `update_diameter()` (so a
branch's diameter can change later, e.g. once the number of wires routed
through it is known, without touching its position/orientation) --
neither is wired into any interaction yet, both exist as ready-to-use
hooks.

**Re-verified after the rewrite**: same full instance-by-instance
cross-check as section 8.5, against a stub-import harness (this module's
own pre-existing circular-import ceiling, see section 7.6, meant it
couldn't be imported standalone the normal way) -- all 111 catalog parts
still match exactly (AABB within 0.05mm, tip positions within 0.01mm) --
neither hard-won bug from section 8.5 regressed during the restructuring.

## 8.7 `__init__` scoping rule, and a `scale3d` fix (2026-09-28)

`_BranchBody.__init__`/`_Hub.__init__` (and their peg-board twins) compute and cache their LOCAL catalog-derived shape data immediately in `__init__`; only the owning transition's world position/angle is kept out of `__init__` and applied later via `update_position()`/`update_angle()`. Re-verified against all 111 catalog parts; **confirmed working in the live app**.

`PJTTransition` has no real scale column (a transition's apparent size comes entirely from its branches' diameters) -- `scale3d` is a property that always returns a cached `Point(1.0, 1.0, 1.0)`, so generic `.bind()`/`.unbind()` toolbar code that expects every selectable object to have one keeps working.

## 8.8 build123d is back, scoped to only the bulb pieces, per part number
## (2026-09-28) -- fixes overlapping-primitives-look-bad-when-selected

Section 4's decision (no boolean ops at all) held for the trunk/hub the
whole time, but the ALL-primitive design has a real visual cost the user
found unacceptable in the live app: every branch's own bulb cylinder and
cap sphere(s) overlap every OTHER branch's, at the shared hub, with no
boolean trim between them -- fine for an ordinary opaque depth-tested
draw (section 4's own reasoning still holds there), but visibly wrong
once a transition is selected/highlighted, since the highlight pass
draws through/across that same untrimmed overlap.

**Decision:** `_Body._build_body_model` (`objects_3d/transition.py`)
unions ONLY the bulb pieces (bulb cylinder + cap sphere(s)) of every
branch that has one -- via `build123d`, real boolean `+` fuse -- into
one shared mesh, cached in a `PooledVBOHandler` keyed by
`f'{part.part_number}:transition'`. This is deliberately narrower than
the old retired `_build_model` pipeline: the hub sphere(s) and every
branch's own trunk cylinder are NOT part of this union and stay on the
plain-primitive path exactly as section 4 describes -- only the bulb
region (the part of the geometry that actually looked bad overlapping)
goes through build123d, and only once, ever, per catalog part number
(never per placed instance, never per edit) -- fixing exactly the
performance/fragility case section 2 documented against the old
pipeline, which re-ran the ENTIRE boolean pipeline on every edit.

**Caching, checked before any branch does real work:** `_Body.rebuild()`
(called by every `Transition.build()`, i.e. every edit) calls
`_build_body_model` every time, but the actual `build123d` work only
ever runs on a genuine first-ever-build for that part number -- `vbo_id
in _vbo.PooledVBOHandler` is checked FIRST, before iterating branches to
build anything, and short-circuits straight to re-resolving the existing
pooled VBO when found (matching `objects_3d/seal.py`'s own established
`PooledVBOHandler` pattern for a build123d-built, part-number-keyed
mesh -- SWS seals already do exactly this). A part number that has
already failed once (`_FAILED_BODY_IDS`, a plain in-memory set, never
cleared -- catalog geometry can't start succeeding mid-session) is also
skipped without re-attempting the expensive fuse.

**Fallback, exactly matching the user's own spec:** "if the bulb pieces
that are available do not intersect for some reason, fall back to
rendering the whole transition exactly like it is being done currently"
-- checked as `len(body.solids()) != 1` (a real single fused solid, not
several disjoint/tangent ones still counted as one `Compound`) OR `not
body.is_valid`, plus a catch-all `try/except Exception` around the whole
build+fuse+mesh pass (covers a `ShapeList`/anything-without-`.wrapped`
result the same way section 2 flagged for the old pipeline, and any
other OCP-level failure). On any of these, every branch's own
`use_body_model(False)` keeps it on the original, always-safe
all-primitive rendering, unchanged.

**Branch-side consequence when the body model IS used:** a branch whose
own bulb IS covered by the shared body VBO (`use_body_model(True)`, only
ever set on a branch that actually has a bulb) trims its own trunk
cylinder back to start at the bulb's own end point (already computed as
`bulb_end`, exactly on the branch's own axis in both the plain and
trunk-`bulb_offset` cases) instead of the branch's root `offset`, with
its length shortened by the same amount -- removing the overlap between
the trunk cylinder and the bulb region entirely, computed once in
`_BranchBody._refresh_world()` (not per-frame). `render()` skips drawing
that branch's own bulb cylinder/sphere(s) in this case (already drawn
once, by the body VBO, for every placed instance of this part).
`hit_test_outer()` was updated to read a dedicated `tip_point` cached
attribute instead of re-deriving the branch's tip from `branch_start` +
`length` -- that combination is only valid for an UNTRIMMED branch_start,
and silently wrong (points too far out) once trimming applies.

**Live-edit staleness, caught and fixed while wiring this up:**
`ui/dialogs/transition_editor/preview.py`'s `PreviewTransition3D` reuses
this exact same `_Body` class for the transition editor dialog's own
live preview -- and that dialog is the ONE place a catalog part's bulb
geometry can actually change while its `part_number` (the VBO's cache
key) stays the same. Its `rebuild()` (called on every debounced field
edit) now evicts `part.part_number + ':transition'` from the pool
(`_vbo.PooledVBOHandler.evict`, an existing, previously-unused hook
built for exactly this "same key, new data" case) before calling
`build()`, so every edit gets a fresh fuse instead of silently reusing
the pre-edit mesh. A normal placed `Transition` never calls `evict` --
its own `rebuild()` calls (branch diameter changes) can never actually
change bulb geometry, so reusing the cached body VBO there is correct,
not stale.

**Not carried further, left as a known follow-up:** saving edited
catalog data back out of this dialog (elsewhere in the dialog's own
code, not touched by this change) does not itself evict every OTHER
already-placed instance's cached body VBO for that part number --a
placed transition elsewhere in the project that already resolved this
part's body VBO before the edit was saved will keep showing the
pre-edit shape until its own `_Body.rebuild()` happens to run again (or
the app restarts). Out of scope for this pass (this task was about
rendering, not the editor's save/commit path); flagged here for whoever
next touches that save flow.

**Not extended to `objects_pegboard/transition.py`** in this pass -- it
has its own independent `_PegBranchBody`/`_PegHub`/`_PegBody` (section
8.6), with a different local-space baseline (each branch is pre-rotated
by the peg-board's own fixed `_FLATTEN` transform baked directly into
its local data), so its own bulb pieces are NOT in the same local space
as the 3D view's and can't share the same cached body VBO without
either rebuilding it twice (once per view, defeating the point of
per-part caching) or reworking the peg-board flatten to be a runtime
transform instead of a baked-in one. Left on its original all-primitive
rendering; the pegboard's own version of the same overlap-when-selected
problem (if the user wants it fixed too) needs its own design pass.

**Validated against the real live catalog** (`harness_designer.db`, all
111 transitions, offline script against real branch rows -- not just
the earlier prototype/audit data): 102/111 fuse into one valid solid and
get the new trimmed-body rendering; 9 fall back cleanly, none crash --
`322A412-25/225-0`, `322A434-25-0`, `322A434-25/225-0`, `362A024-25-0`,
`362A024-25/225-0`, `362A024-25/86-0`, `362A114-25-0`,
`362A114-25/225-0` all produce 3 disjoint solids (their bulbs don't
actually reach each other), and `342A012-25-G05/225-0` produces one
solid that build123d itself reports as `is_valid == False`. The five
`362A0*`/`362A1*` failures are the same "trunk has no bulb of its own"
parts section 4's own hub-sphere rationale is built around -- expected:
without the trunk's own bulb in the mix, the remaining branches' bulbs
have less to converge on. Timed on the worst (5-bulb, trunk
`bulb_offset`) real catalog part, `562A011-25-0`: ~170ms to fuse + ~200ms
to mesh, ~370ms total -- paid once per part number, ever, not per edit
(contrast section 5's 82-340ms *per edit* for the old full pipeline).

## 8.9 `_Hub` sphere removed entirely (2026-09-28) -- current state

The separate hub sphere (`_Hub`, one per shared branch-root point, section 4's original "Hub sphere" design) no longer exists in `objects_3d/transition.py` -- fully redundant once 8.8's build123d bulb union covers the same shared point.

**Still open, not chased further:** without either a bulb's own cap sphere or `_Hub`, a branch with a flat-capped cylinder meeting others at the vertex may show a visible gap/seam there. If it turns out to matter visually, the fix belongs inside `_build_body_model`'s own union (widen the bulb cylinders to self-cover the gap, or add a sphere at the shared vertex into the fused body) -- not a revival of `_Hub`.

## 8.10 `build_bulb_solid` rules -- confirmed working in the live app (2026-09-28)

Load-bearing rules from this fix pass, still true of the current code (`objects_3d/transition.py`):

1. **`bulb_offset is None` vs `bulb_offset == [0, 0, 0]` are NOT the same state and must never be collapsed.** `NULL` means "no bulb offset of its own" (section 3); a stored `[0.0, 0.0, 0.0]` is real data saying this branch DOES have its own bulb offset (which happens to sit at zero) and still needs the two-sphere treatment. Always check `is not None`, never truthiness.
2. **The far-end sphere's position is angle-aware**, not a hardcoded local -X shift: `pos = Point(round(bulb_len * cos(r), 6), round(bulb_len * sin(r), 6), 0.0) + bulb_offset` where `r = radians(angle.z)`. `_refresh_world()`'s `bulb_end` (where the trimmed branch cylinder starts once the shared body VBO covers the bulb, section 8.8) uses the exact same formula, so it always agrees with where `build_bulb_solid()` actually places the far sphere.
3. `_build_body_model`'s `is_valid`/`len(solids()) == 1` check (added in 8.8) was removed entirely -- it rejected real parts that render fine; solid-validity semantics don't determine whether the triangulated mesh looks right (same reasoning section 4 uses against boolean ops generally). The one failure mode that matters (`build_bulb_solid()` returning a `ShapeList`, no `.wrapped`) surfaces on its own as an `AttributeError`, caught by the existing `except Exception`.

**Confirmed working in the live app.**

## 8.11 `Branch` unified -- the old pickable tip-marker object retired
## entirely, `Transition` now owns all per-branch interaction (2026-09-28)

Per the user's own steer: the amount of real interaction a single
branch ever needs is small (light up while dragging a wire/bundle end
near it, if it fits -- three concrete cases: dragging a wire, dropping a
transition onto a bundle end, dragging a bundle's own end), so a branch
does not need to be its own independently-picked scene object at all.

**What changed, in `objects_3d/transition.py`:**

- The old `Branch(_base_3d.Base3D)` -- a small pickable tip-marker
  sphere, registered with the canvas, with its own `identify()`/
  `diameter` property that wrote to the database and triggered a
  rebuild -- is gone entirely.
- `_BranchBody` (this file's own geometry cache, section 4 onward) is
  RENAMED to `Branch` -- now the sole "branch" object, still not a
  `Base3D` subclass and still never registered with the canvas as a
  pickable object of its own. It gained an optional `db_obj`
  (`PJTTransitionBranch`, `None` only for the transition editor
  dialog's preview) so it can read/persist diameter and its own WORLD
  tip position directly, with no separate tip-marker object standing in
  between any more:
  - `min_diameter`/`max_diameter` properties (catalog `min_dia`/
    `max_dia`) -- what the old tip-marker's own properties of the same
    name used to read off a longer `db_obj.transition.part.branches[...]`
    chain.
  - `set_diameter(diameter)` writes `db_obj.diameter` (a no-op with no
    `db_obj`) and recomputes the render cache via `update_diameter` --
    distinct from `update_diameter` itself, which ALSO seeds the cache
    at construction time from whatever's already stored, and must never
    write back (that's not a change, just reading what's there).
  - `write_tip_to_db(force=False)` persists `tip_point` (this branch's
    real WORLD end position, current after `update_position`/
    `update_angle`) into `db_obj.position3d` -- only when that stored
    point is still at the origin, unless `force` -- the same guard the
    old design had, so a branch already snapped to a bundle end (its
    position3d row shared with that bundle's own endpoint) doesn't get
    silently reset by an unrelated diameter-only rebuild.
  - `hit_test_sphere(point)` replaces the never-wired `hit_test_outer`
    (distance-to-outer-segment) with exactly the user's own spec: a
    sphere at `tip_point`, radius this branch's own current diameter / 2.
- `_Body.rebuild(part, branch_db_objs)` takes a plain list of each
  branch's own `PJTTransitionBranch` (or `None`), indexed by catalog
  `idx`, instead of a list of tip-marker objects to read/write through.
  Tip persistence moved out of `rebuild()` into a new
  `write_tips_to_db(force=False)`, called separately once
  `apply_transform` has run (tip_point is only correct in WORLD space
  after that).
- `_Body.render()`'s highlighting changed from a single `highlighted_idx`/
  `highlight_material` pair to a `branch_materials: dict[int,
  GLMaterial]` -- multiple branches can need DIFFERENT override colors
  at once (e.g. every branch lit green/orange by fit while dragging a
  wire nearby), which one index/material pair could never express.
- `Transition` gained the actual interaction surface the old tip-marker
  objects used to provide piecemeal, now centralized:
  - `branches` (public property -- `self._body.branches`) -- fixes a
    real pre-existing bug this surfaced: `handlers/transition_handler.py`
    already had TWO call sites reading `t_obj.obj3d.branches` (with a
    `# TODO: Figure out the missing branches attribute` next to each),
    which would have raised `AttributeError` the moment either
    ever actually ran -- there was no `branches` attribute at all
    before this.
  - `branch_fits(branch, diameter)` -- `min_diameter <= diameter <=
    max_diameter`, the one compatibility rule all three "does this
    branch light up" cases share.
  - `hit_test_branch(point)` -- closest branch whose sphere contains a
    real world-space point the caller already has (a dragged wire/
    bundle end's own current position).
  - `hit_test_branch_ray(origin, direc)` -- real ray-sphere
    intersection, for screen-space mouse hover where depth isn't
    otherwise known (the bundle-end-to-branch snap case). Callers get
    the ray from `gl.object_picker._build_ray(mouse_pos, camera)` -- the
    exact same construction the generic canvas picker itself uses,
    reused directly rather than duplicated.
  - `highlight_branch`/`clear_branch_highlight`/`clear_branch_highlights`/
    `highlight_branches_for_diameter` -- manage `_branch_materials`,
    threaded through to `_Body.render()` via a new `Transition.
    _render_geometry` override (the generic `BaseVar._render_geometry`
    has no slot for this; overriding it is the only way to actually get
    an extra kwarg to the VBO's own `render()`).

**Other files fixed to match (all direct consequences of the above, not
separate decisions):**

- `add_handlers/editor_3d/transition.py` (the ONE live, reachable
  interactive path this affects -- bundle-end-snap placement's own
  branch-hover-and-pick): swapped `gl.object_picker.find_object` +
  `isinstance(selected, Branch)` + `selected.identify(mat)` for
  `Transition.hit_test_branch_ray`/`branch_fits`/`highlight_branch`/
  `clear_branch_highlight`.
- `objects_pegboard/transition.py`: `_PegBody(self._part, obj3d.
  _branches)`/`._PegBody.rebuild(self._part, obj3d._branches)` read a
  now-nonexistent private attribute -- fixed to `obj3d.branches` (the
  new public property; `_PegBody.rebuild` only ever reads `.diameter`
  off each entry, which the new `Branch` still has, so this is a clean
  drop-in swap, not a deeper change).
- `ui/dialogs/transition_editor/preview.py`: `PreviewTransition3D`
  builds a plain `[None] * branch_count` in place of constructing
  tip-marker `Branch` objects one by one; sets `self._branch_materials`
  itself (bypasses `Transition.__init__` entirely, so nothing else does
  this for it).
- `ui/dialogs/transition_routing.py`: `_update_branch_3d` read
  `self._transition_3d._branches` (same now-nonexistent attribute) and
  set `branch_3d.diameter = new_diameter` (the old tip-marker's own
  setter, which wrote to the database itself). The database write
  already happens directly on `branch_db` a few lines earlier in the
  real caller, so the fix is simpler than a like-for-like swap: just
  call `Transition.build()`, which reseeds every branch's diameter
  fresh from `db_obj.diameter` on its own.
- `handlers/transition_handler.py`'s `RouteThroughTransitionHandler`/
  `RoutedWireHandler` (both explicitly documented, before this session,
  as dead code with no UI entry point anywhere in the app) had their
  branch highlighting/clearing and (for `RouteThroughTransitionHandler`
  only) branch-picking updated to the new API, so they at least don't
  hard-crash if ever revived. `RoutedWireHandler`'s OWN branch-picking
  (`_handle_routing_click`/`_handle_exit_click`, a mixed wire/bundle/
  branch `isinstance` chain off one `find_object` call) was left as is
  -- now structurally unreachable (that `isinstance` against a branch
  can never be `True` any more) rather than just unwired, but fixing it
  properly needs the same ray-based swap folded into its own mixed pick
  logic, and there is still no way to exercise or verify it. See that
  module's own updated docstring.

## 8.12 Peg-board view brought up to full parity with the 3D view
## (2026-09-28)

`objects_pegboard/transition.py` -- previously the all-primitive design
from before section 8.8 (its own `_PegBranchBody`/`_PegHub`/`_PegBody`,
no build123d, no per-branch interaction API) -- was rewritten from
scratch to mirror everything sections 8.8-8.11 did for the 3D view:

- `_PegBranchBody` renamed `_PegBranch` (kept `_Peg`-prefixed and
  private -- unlike the 3D view's `Branch`, there was never an old
  pickable object of the same name to fold into it, and nothing outside
  this file ever referenced it, so there's no naming collision to
  resolve). Gained the same `db_obj` (`PJTTransitionBranch`),
  `set_diameter`, `write_tip_to_db`, `hit_test_sphere`, and
  `build_bulb_solid` the 3D view's `Branch` did.
- `_PegHub` removed entirely, matching section 8.9's removal of `_Hub`.
- `_PegBody` gained the same `_build_body_model` (pooled build123d
  bulb-union body VBO) and `branch_materials`-dict highlighting
  `_Body` did.
- `Transition` (peg-board) gained the same `branches`/`branch_fits`/
  `hit_test_branch`/`hit_test_branch_ray`/`highlight_branch`/
  `clear_branch_highlight`/`clear_branch_highlights`/
  `highlight_branches_for_diameter`/`_render_geometry` override the 3D
  view's `Transition` did. `rebuild()` (never had any caller of its own)
  renamed `build()` for consistency, and rebuilt to construct its OWN
  branches directly from `db_obj.branch1..branch6` rather than reading
  the 3D view's own branch list -- the two views' bodies were already
  documented as deliberately never shared (`_PegBody`'s own docstring,
  predating this session), so this removes the one place they still
  depended on each other at all.

**Two real differences from a line-for-line copy, both about the
peg-board's own fixed 90-degree-about-X "flatten"** (pre-existing in
this file since before this session, as `_FLATTEN =
Angle.from_euler(-90, 0, 0)` -- baked into every branch's own LOCAL
offset/direction/bulb_offset at construction, so the peg-board renders
correctly flat with `angle_pegboard` at identity, and that stored
angle's own X component is never touched again after that -- it stays
a further, freely user-adjustable rotation on top of the bake, exactly
as this file's own pre-existing docstring already described):

1. **The primitive/fallback path** (`_PegBranch._refresh_world`) needed
   one small addition beyond a plain copy: the direct port of the 3D
   view's `cap_shift` (the bulb's own far-end offset, computed from this
   branch's own RAW, un-flattened `angle.z`) must ALSO be rotated by
   `_FLATTEN` before combining it with the already-flattened
   `_local_offset`/`_local_bulb_offset` -- otherwise the trimmed
   branch's own start point (used whenever the body-VBO path is active)
   would mix a flattened offset with an unflattened shift, the same
   class of bug section 8.10 point 3 already found and fixed once in
   the 3D view's own code (there, between two different UNFLATTENED
   values; here, between one flattened and one unflattened value).
2. **The build123d body-VBO path** (`_PegBody._build_body_model`) does
   NOT try to compose the flatten into each branch's own per-piece
   euler-degree placement math (`Plane(...).rotated(angle.as_euler_
   float)`, `math.radians(angle.z)`) -- doing that would mean
   decomposing a composed rotation back into a NEW set of stored euler
   angles, the "genuinely delicate" operation this codebase already
   goes out of its way to avoid everywhere else it can (see
   `handlers.transition_handler._apply_rotation`'s own docstring on
   exactly this point). Instead, `_PegBranch.build_bulb_solid()` is a
   byte-for-byte copy of the 3D view's own method -- builds in the
   SAME native/catalog orientation, no flatten at all -- and
   `_build_body_model` applies ONE single-axis `build123d.Axis(origin=
   (0, 0, 0), direction=(1, 0, 0))` rotation of exactly -90 degrees to
   the WHOLE fused body, once, right before meshing. A single-axis
   `build123d` rotation is exact and unambiguous (never a decomposition
   risk, unlike composing/storing new euler angles) -- confirmed
   empirically (2026-09-28) to agree exactly with `_FLATTEN` itself:
   both `Point() @= Angle.from_euler(-90, 0, 0)` and `Vector().rotate(
   Axis(origin=(0,0,0), direction=(1,0,0)), -90.0)` map `(0, 1, 0)` to
   `(0, ~0, -1)`. Re-validated against all 111 real catalog parts after
   the rewrite: every one fuses and meshes successfully, both before
   and after the whole-body flatten rotation, with the fused solid
   count/validity unchanged by the rotation (as expected -- rotating a
   solid can never change how many pieces it's made of).

Pooled under its own VBO id, `part_number + ':transition:pegboard'` --
never the 3D view's own `':transition'` id, since the two meshes are
genuinely different (one is rotated flat, one isn't) and could never
correctly share a pool entry. Its own separate `_FAILED_BODY_IDS` set
too, kept apart from the 3D view's for the same reason
`_branch_direction` is duplicated rather than imported -- this whole
apparatus belongs directly in each view's own file (a pre-existing,
pre-this-session convention in this exact module).

## 9. Open questions

- ~~Per-branch picking/hit-testing is still unsolved~~ **Resolved --
  already handled.** `gl.object_picker.find_object(mouse_pos, camera,
  canvas)` is the real, generic canvas picking system and already
  resolves picks down to individual `Base3D` objects, including the
  small tip-marker `Branch` spheres, not just "the whole transition" --
  no new picking mechanism needed for the dialog's branch-highlighting or
  future per-branch drag interaction (TRANSITION_EDITOR_DIALOG.md
  sections 5-6).
- Flanges (`TransitionBranch.flange_height`/`.flange_width` -- real
  catalog columns, with real spin-control UI already, see
  TRANSITION_EDITOR_DIALOG.md section 2) are not drawn by
  `TransitionModel` at all yet. Deferred, not forgotten.
- Section 7 step 4 (peg-board's per-piece representation) turned out not
  to need a design pass at all -- resolved, see section 7's own entry.

## 10. Decision log

- **2026-09-26/27**: replace `_build_model`'s OCC boolean pipeline with
  cylinder+sphere primitives, no boolean operation, depth-tested opaque
  overlap. Confirmed by the user: "so long as the depth order is correct in
  OpenGL it shouldn't matter" that build123d's trim is gone.
- **2026-09-27**: hub sphere added at every distinct branch root point,
  sized to the largest diameter converging there -- a deliberate
  improvement over `_build_model`'s accidental (bulb-cylinder-overlap)
  hub closure, motivated by `362A024-25-0`'s trunk having no bulb of its
  own.
- **2026-09-27**: the `bulb_offset` two-sphere trunk case is a **literal,
  faithful port** of `_build_model`, not simplified away -- user correction
  after an initial pass had dropped the near-vertex sphere as "redundant
  with the hub sphere." It is not redundant: it's real data the model must
  render, even where (section 6) that data is itself wrong.
- **2026-09-27**: branch tube/bulb tip is deliberately left open (no end
  cap) -- user: "a branch having an open end is either going to be filled
  with wires or it will be attached to a bundle." Not a defect to fix.
- **2026-09-27**: `cone` is not used anywhere in this design -- only
  `cylinder` and `sphere` (user confirmed, ruling out a tapered-bulb
  primitive as an alternative to the wide-cylinder-plus-cap-sphere shape
  already in section 4).
- **2026-09-27**: euler angles (not quaternions) are the permanent storage
  format for `angle`, confirmed final -- see section 3 for the gimbal-lock
  reasoning (only occurs converting *to* euler, never *from* it, and this
  code only ever does the latter).
- **2026-09-27**: the primitive design's real long-term purpose extends
  past rendering -- it is meant to become the save format for a future
  user-facing dialog that lets people build their own transitions/boots/etc.
  in a 3D environment, with an explicitly low accuracy bar ("close ...
  for the sizes and where things connect," not a precise reproduction). See
  section 8.
- **2026-09-27**: section 7 ported into the real app as
  `objects.transition_model.TransitionModel`, a `VBOHandlerBase`-compatible
  object (not the "per-branch `Base3D` objects" or "flat instance list
  drawn directly" options step 1 originally posed -- a third shape,
  matching `shapes.text.Text`'s own established multi-piece-VBO pattern,
  per the user's own steer) standing in directly as a transition's
  `self._vbo`. All 111 catalog parts verified against the scratch's own
  already-validated math. Full record: TRANSITION_EDITOR_DIALOG.md
  sections 7.5-7.10.
- **2026-09-27**: asked to review this file for missed design steps,
  found step 5 (`global_db.Transition.branches`'s `res[idx - 1]`
  off-by-one) had never actually been fixed, despite being ported "after"
  it in the original step order and explicitly depending on it being
  correct first. Fixed at the root. See section 6's updated entry for the
  real, previously-silent correctness consequences across every
  by-position consumer of that list.
- **2026-09-28**: build123d reintroduced, but scoped to ONLY each
  branch's own bulb pieces, unioned once per catalog part number and
  cached in a pooled VBO (`part_number + ':transition'`) -- motivated by
  the all-primitive design's untrimmed bulb-cylinder overlap looking
  visibly wrong when a transition is selected/highlighted. Falls back to
  the unchanged all-primitive rendering whenever a part's own bulbs
  don't fuse into one valid solid (confirmed safe against all 111 real
  catalog parts: 102 succeed, 9 fall back cleanly, zero crashes). See
  section 8.8 for the full design, validation, and the explicit
  `objects_pegboard/transition.py` scoping gap.
- **2026-09-28**: the separate `_Hub` sphere removed entirely (section
  8.9) -- redundant with the build123d bulb union once the person
  actually iterating on `build_bulb_solid` confirmed it visually.
- **2026-09-28**: `_build_body_model`'s `is_valid`/`len(solids()) == 1`
  check removed entirely (section 8.10, user decision) -- it rejected
  real parts that render fine; neither check means anything about
  whether the resulting triangulated mesh looks right, same reasoning
  section 4 already used against boolean ops generally. The only real
  failure mode (a `ShapeList` with no `.wrapped`) still gets caught, as
  a plain exception from `convert_model_to_mesh()`, no explicit check
  needed.
- **2026-09-28**: `bulb_offset is None` (no bulb offset) and
  `bulb_offset == [0, 0, 0]` (a real, explicit zero-valued bulb offset)
  are confirmed NOT the same state and must never be collapsed -- see
  section 8.10 point 1 for the real branch (`302A024-25/225-0` idx 2)
  this distinction mattered for.
- **2026-09-28**: the old pickable tip-marker `Branch` (a `Base3D`
  object registered with the canvas) retired entirely -- `_BranchBody`
  renamed to `Branch`, gains an optional `db_obj` so it owns its own
  diameter/tip-position persistence directly, and `Transition` now owns
  all real per-branch interaction (`hit_test_branch`/
  `hit_test_branch_ray`/`highlight_branch`/`branch_fits`) instead of
  each branch being independently picked. Motivated by how little real
  interaction a branch ever needs (three light-up-if-compatible cases).
  See section 8.11 for the full design and every other file this
  touched to keep working.
- **2026-09-28**: `objects_pegboard/transition.py` brought up to full
  parity with the 3D view (build123d bulb-union body VBO, no separate
  hub, per-branch interaction API) -- see section 8.12 for the full
  design, including the two real differences from a line-for-line copy
  (both about correctly applying the peg-board's own pre-existing fixed
  90-degree-about-X flatten to the new build123d-based pieces) and the
  empirical confirmation that a single-axis `build123d` rotation
  applied once to the whole fused body agrees exactly with `_FLATTEN`.
