# Twisted wires and the per-conductor table (design, started 2026-11-03)

Built so far: see section 0 (the table and ids, the layered images, and since 2026-11-05 the first version of the 3D rendering). Written down on purpose (MEMORY.md: "write down a detailed verbal spec
immediately"). Add new decisions HERE.

## 0. Status (end of the 2026-11-03 session)

BUILT (compiled and, for the builder, test-built; the app was NOT launched, no tests exist by project rule):
- Layered preview images (2026-11-04, approved by the user from a preview sheet; used through `database/global_db/wire_image.py`, see below):
  `diagnostics/make_wire_layers.py` generates `twisted2_*`, `twisted3_*`, `cable_*` and `coax_*` PNGs in
  `image/images`; `image/wire_images.py` holds one `Image` subclass per cable type (`TwistedWireImage`, `CableImage`,
  `CoaxImage`; everything else in it is private) which assemble the layers and cache themselves by colour with a
  metaclass (see `image/MAP.md`). One stripe layer per conductor; at most three
  conductors are drawn; coax dielectric and shield colours are fixed by the caller (the catalog has neither).
  `database/global_db/wire_image.py` `build_wire_image(wire)` picks the builder (single wire, twisted pair / triple, jacketed
  or shielded cable, coax) and is used by the wire editor, the peg-board wire table, the BOM and the circuit editor; a cable
  with no `wire_conductors` rows, and the Ribbon wire type (see the TODO in section 7), still get no image. Compile-checked only, the app was not run.
- `wire_conductors` table, both repos: app `database/create_database/wire_conductors.py`,
  `global_db/wire_conductor.py` (`WireConductorsTable`, `WireConductor`), `global_db/mixins/wire_conductor.py`
  (`Wire.conductors`), registered in `global_db/bases.py` (`GLBTables.wire_conductors_table`); builder
  `builder/create_database/wire_conductors.py`, registered in `builder/build_database.py`. Columns as in section 2
  (the user confirmed `od_mm` and the size columns belong there; `idx` was added).
- "No color": `id_generator.NO_COLOR_UUID` = `00000000000000000000010000010000` (the layout-correct global id with
  timestamp 1), in both repos. Nil stays Black. `wires.color_id` / `stripe_color_id` default to it; a cable HAS an
  outer jacket when its `color_id` is not it. In the builder `get_color_id(con, name, unset=None)` takes the id to
  return for a blank or unknown name; only the wires (and conductors) pass `NO_COLOR_UUID`, so every other table
  still maps an empty colour to the nil id as before. The wire GENERATION code lives only in the database repo; the
  app has just the schema (`create_database/wire_conductors.py`, the column defaults in `create_database/wires.py`)
  and the readers. Code that read "nil colour = no colour" was moved to the new id:
  `Wire.stripe_color`, `ui/editor_db/wire.py`, `ui/pegboard_table/wire_table.py`, `ui/editor_circuit/editor_widget.py`
  `_unset`.
- STATIC CATALOG IDS (builder): `static_row_id(table, *key)` replaced the clock at all ~60 insert sites. A key
  gets the next number from a counter the first time it is seen and is written to `builder/row_ids.txt`
  (`<number> <fingerprint>`, COMMIT IT; 17 MB for 723,676 rows because the fingerprint is an 8-byte hash of
  the key, a readable ledger was 65 MB). A bare counter is not enough (adding one part in the middle would shift
  every later id); the remembered counter is. Verified by building three times (ledger present twice, ledger
  deleted once): every table identical in all three, except `settings`, which stores the build's output folder.
  The numbers sit in the row id's timestamp field, far below the clock values (about 1.8e18) the app issues to rows
  a user creates, so a downloaded catalog can be merged into a user's database without a clash. Hard rule, enforced in both id generators
  (`CATALOG_ID_CEILING` = 2**40, the same value in both repos): the catalog builder refuses a number at or above it,
  and the app's `generate_global_row_id` refuses a clock value at or below it, so a user-added part (clock) and a
  preloaded part (sequential) can never collide. A part whose
  natural key changes upstream is a new row. `bosch_convert_all.py` (not part of the build) still writes a random
  uuid4 into `models3d.uuid`.
- Generator (`harness_designer_database/scripts/wire_builder.py`): added `M22759/32` (TE datasheet), `/33`, `/43`,
  `/44` (Glenair GS22759 datasheets; conductor dia = midpoint of min/max, OD = nominal + tolerance, XL-ETFE, min
  temp -65), their NEMA symbols (`SB` TE; `SC`, `SP`, `SR` from a third-party Scribd copy, unverified) for the
  M27500 cable part numbers; an unjacketed cable's colour is `None`, a jacketed one's follows its jacket
  (`06`, `14` White, `05` Natural), replacing the old `Vanilla` placeholder; and `Universal/wire_conductors.json`
  (one entry per CABLE: shared `common` fields plus the conductors in order, expanded by the builder to
  215,600 rows for 43,120 cables). `Universal/wires.json` was regenerated (a strict superset of the old file:
  all 68,250 parts kept, 8,750 new; only `mfg` TE -> TE Connectivity and the colour changed).
- M27500 numbering and colours, corrected (2026-11-03; the first version had three errors):
  - the trailing `T` meant "twisted" but M27500 has no twist code, so it is gone, and so are the untwisted
    twins: every cable of 2+ conductors is one part number with a twist of 1 per inch (a seller's M27500-20SB2U00
    listing: "1 twist per inch as per MIL standards"; this replaced a table of per-AWG guesses; one conductor has
    no twist);
  - the colour-code character after `M27500` sets the conductor colours: `-` (default) is WHITE with a stripe from
    the second conductor on (blue, orange, green, red, black, yellow, violet), `A` is the same sequence in
    SOLID colours and is generated as `M27500A...` (source: Wiremasters' guide, secondary; the checked example is
    M27500-20SB2U00 = 2 x M22759/32, white + white/blue, which now matches);
  - not done: 9-15 conductors (the guide says 1-15 are valid; the cable-size table stops at 8) and the unshielded,
    unjacketed 1-conductor form (valid per the guide but it duplicates the plain wire).
- Colour-combination twisted pairs (automotive style, 20-28 AWG, M22759/32 and M22759/18, tin-plated copper, no
  shield and no jacket so `color` is "None", 1 twist per inch; 44,550 parts, 4,950 per sheet and size). There is no MIL
  number for an arbitrary colour pair, so the numbers copy how sellers number them (the user supplied the examples):
  both solid `M22759/32-24-5/4-1TPI`; any striped `M22759/18-22-9-9/6` (`base/stripe`, MIL-STD-681 digits). A seller
  example at 18 AWG (`M22759/32-18-9-9/6`, 2 TPI) is not generated: the sizes asked for were 20-28, and the pairs
  all use 1 TPI. These numbers are provisional until the user has checked more sellers.
- Splitting: the generator writes `Universal/wires/<model>.json` (one file per wire model: a sheet's own wires
  `M22759-32`, the cables built on it `M27500-M22759-32`, the pairs `TP-M22759-32-22AWG`) and the matching
  `Universal/wire_conductors/<model>.json`; the builder reads every file of both folders in sorted order. The old
  single `Universal/wires.json` and `wire_conductors.json` are deleted. Largest file 4.3 MB.

- TWISTED RENDERING, first version (2026-11-05; tested with throwaway scripts only: an offscreen GL render through the real
  `FacesProgram`, and a numeric copy of the shader maths; the app itself was NOT run, and the DB side was not run against a database):
  - Where it lives (a deviation from section 5, which asked for a new `Program` subclass): the faces VERTEX SHADER got a twist mode,
    switched by the `twistRings` uniform (0 = off, the default), because every canvas, the headlight, the scene light and the reflection
    pass set their per-frame uniforms on `shaders.faces` only, so a second program would have needed all of that repeated. The geometry
    and fragment stages are shared, so reflections, lighting and materials work unchanged. `gl/shaders/faces/vertex.vert` `twistVertex`,
    `FacesProgram.twist_*` in `gl/shaders/program.py`.
  - Vertices come from `gl_VertexID` (no attributes, an empty VAO): `TWIST_SIDES` = 16 sides, `twistRings` rings, rings every
    22.5 degrees of twist (`SAMPLES_PER_TURN` = 16), and when an end has a mitre at least one ring per outer radius, at most 8000.
  - `shapes/twisted_wire.py`: `profile` (conductor circles: touching equal circles, `c = r / sin(pi / n)`; a pair r = OD / 4, a triple
    r = OD / 4.309), `plan` (phase carry and mitre, section 5, as designed), `ring_count`, `TUBE.draw`.
  - Phase carry and mitre are the formulas of section 5. Checked numerically over 2000 random bends of 5-150 degrees: the end ring of
    one segment and the start ring of the next agree to 1e-13 mm (4e-14 for the carry alone). The taper `D` is twice the largest shift
    (`2 R tan(bend / 2)`), limited to half the segment, so a sharp bend on a short segment can still fold; a 120 degree bend draws a
    pointed outside corner, as a rigid mitre must.
  - Stripe: `fragStripe` (angular distance from the stripe's centre) goes vertex -> geometry -> fragment; the stripe is 60 degrees wide
    and sits on the side of the conductor facing away from the cable's axis (snapped to one of the 16 sides so the distance is exact);
    the fragment shader blends the stripe's ambient / diffuse / specular in over one pixel. The rigid twist carries it as a helix.
  - Which conductors stripe and where: whichever `wire_conductors` rows have a stripe colour (the builder's data), on the outward side;
    the lay is a right-hand (Z) twist, since TE and the mil-spec data give no direction.
  - DB side: `WireConductorMixin.is_twisted` (tpi above 0, 2 or MORE conductors since 2026-11-05, no jacket colour, a conductor row each) and
    `conductor_colors`. `objects_3d/wire.py`: `_build_twist`, `_twist_segments` (cached in `_twist_plan`, cleared by
    `_recalculate_geometry`), `_render_twisted`.
  - Not done for a twisted wire: the debug edge / normal / vertex passes (no twist mode in those programs), the bare-conductor look at a
    crimp end, `ray_trace_parts` (still the plain tube), LOD (rings do not thin out with distance), the fan-out (section 8), and the
    pegboard / schematic views (3D only).
  - TE wires: most have no `od_mm` (401 of 2,962 twisted ones do) and so draw at zero size, like every TE wire with no `od_mm` does
    in the plain tube path; that is a catalog data gap, not a rendering one.

NOT DONE:
- The row id ledger keeps the numbers of part numbers that no longer exist (they are never reused, and the first
  versions of the M27500 and pair numbers are in it), which is harmless.
- Slash sheets /34, /35, /41, /42, /45, /46 (also /1, /2, /14, /15, which are in MIL-W-22759E's similarity
  groups): no source with the full table was reachable (Glenair returned 403 for them; the distributor pages lack the
  conductor diameter). `MIL-W-22759E.PDF` (the base spec, 43 pages, a bad OCR) holds no per-AWG tables, only the list
  of slash sheets; the Amphenol CIT `M22759.pdf` covers exactly the families the generator already had
  (/5-/12, /16-/23, /28-/31, /80-/92).
- `Wire.tpi` is hinted `float` now (the `int` hint noted here earlier was already fixed).
- The live `harness_designer.db` has no `wire_conductors` table and old colour ids until it is rebuilt from the builder.

## 1. Goal

Render a multi-conductor wire in 3D as what it really is: a twisted pair/triple (conductors visible, no
jacket) when it is unshielded and has 2 or more conductors (the 2-or-3 limit was dropped 2026-11-05), otherwise a plain jacketed tube. The twist rate
is the existing `wires.tpi` (turns per inch). The concentric-bundle packing (`CONCENTRIC_TWIST_DESIGN.md`)
is NOT what this renders; this is the twisted wire itself.

## 2. New table: one row per conductor inside a multi-conductor wire (user spec, 2026-11-03)

The `wires` table stays as it is: it describes the OUTSIDE of a multi-conductor wire. The new table
describes each INDIVIDUAL conductor inside one.

User's rules:
- No unique column except the row id (no part number, no `UNIQUE (wire_id, idx)`).
- Holds the things that may differ conductor to conductor: size information, colour, stripe colour, core
  material, etc.
- A column for the row id of the cable (`wire_id` -> `wires.id`).

Columns (built; `od_mm` and the size columns confirmed by the user 2026-11-03, `idx` added by me; mirrors the same-named `wires` columns so the same
lookup helpers and property code can be reused):

| column | type | notes |
|---|---|---|
| `id` | UUID, primary | |
| `wire_id` | UUID, NOT NULL, FK `wires.id` | the cable this conductor sits in; index it on SQLite |
| `idx` | int, NOT NULL | place inside the cable (needed to order conductors and to pick which one is striped); not in the user's list, flagged for confirmation |
| `color_id` | UUID, NIL default | insulation colour of THIS conductor |
| `stripe_color_id` | UUID, NIL default | NIL = no stripe |
| `core_material_id` | UUID, NIL default, FK `platings.id` | same as `wires.core_material_id` (plating of the copper) |
| `material_id` | UUID, NIL default | insulation material, same as `wires.material_id` |
| `wire_size_dia` | float, NULL | mm; the METAL (stranded) conductor diameter, see section 3 |
| `wire_size_cross` | float, NULL | mm^2 |
| `wire_size_awg` | int, NULL | |
| `strands` | int, default 1 | |
| `od_mm` | float | OD over this conductor's insulation (not in the catalog today; see section 3) |
| `resistance_1km` | float, default 0 | |

Left out as cable-level: `part_number`, `description`, mfg/family/series, temps, image/datasheet/cad,
`weight_1km`, `volts`, `shielded`, `tpi`, `num_conductors`, `wire_type_id`.

Open column questions: a free-text label/function ("+", "signal", "drain")? a flag for a bare drain wire?
what `wires.color_id` means once the conductors carry their own colours (jacket colour only)?

User decision 2026-11-03: the conductor table carries the size information AND `od_mm` (both already in
the list above).

### 2a. Does the cable have an outer jacket? (user decision 2026-11-03: use the colour)

`wires.color_id` is the JACKET colour; a "no color" row means NO outer jacket (the conductors show, as on
an unshielded twisted pair). This replaces the earlier "jacket if shielded or more than 3 conductors" rule.
The user will pick the fixed id for "no color" (it must never change).

What the data shows (checked 2026-11-03, copy of the live DB):
- The all-zero NIL id is a REAL row in `colors`, and it is named "Black" (rgb 0x404040FF). It is the
  `add_color(id=0)` case in `create_database/colors.py`: the catalog JSON's id 0 is stored as NIL. Every
  `*color_id` column defaults to NIL, so NIL currently means both "Black" and "not set".
- A separate "None" row (rgb 0) exists with a GENERATED id (`...ACB719BA46...`), so it is not stable
  across database builds. It is used by only 5 splices; no wire uses it.
- `wires.color_id` is NIL on 22,812 wires (19,898 of them multi-conductor, ALL Molex Premo-Flex FFC
  jumpers, i.e. an unset colour; 155 of those mention "black" in the description) and `stripe_color_id`
  is NIL on 68,785 (everything, so "no stripe" is already NIL and a black stripe cannot be stored).
- Housings (29,977), terminals, covers, boots etc. also sit on NIL.

CORRECTION (user, 2026-11-03): NIL = "Black" is intentional, not a naming mistake -- black is colour
code 0 in the mil-spec colour code (MIL-STD-681), so Black owns the all-zero id. My first suggestion to
rename the NIL row to "None" was wrong. The real defect is that NIL ALSO doubles as "not set" in every
colour column default (and `Wire.stripe_color` returns None for NIL, so a black stripe cannot exist).

Fix to make (proposal, user is choosing the id):
- Keep NIL = Black.
- Give "no color" its own FIXED, hard-coded id (a constant in `database/id_generator.py` next to
  `NIL_UUID`, and in the sibling repo's own copy, `builder/id_generator.py`), and have the builder pin the
  existing "None" row to it instead of a generated id. THE ID MUST FOLLOW THE ROW-ID LAYOUT (below); my
  first suggestion, the all-ones UUID, breaks it and is WITHDRAWN.
- Use it as the default and as the "no colour" value for `wires.color_id` (no jacket), `wires.stripe_color_id`
  (no stripe) and the same two columns of the conductor table. Other catalog tables (housings, terminals,
  covers, boots ...) are a separate question; they can stay on NIL until someone wants "no colour" there.
- Touch points: the column defaults in `create_database/wires.py`; `get_color_id` in
  `create_database/colors.py` (empty name -> the None id; an unknown name currently also falls to NIL and
  prints MISSING COLOR); the `b'\x00' * 16` test in `Wire.stripe_color` (`global_db/wire.py` ~1053) and
  anything that tests `color_id` against NIL; the sibling `harness_designer_database` repo's colour build.
- Rebuilding fixes the "which NIL wires are really black" problem: the builder looks the colour up BY NAME,
  so "Black" still maps to NIL and an empty source colour maps to the None id. The 22,812 wires on NIL today
  stay ambiguous until the database is rebuilt from source.

Row-id rules checked (2026-11-03, read `database/id_generator.py`, `project_db/pjt_bases.py`, the
`global_db/mixins/base.py` NIL notes; measured on the DB copy):
- Layout, MSB first: `[project_id 24 bits][timestamp 64 bits][reserved 20][version 4][user_id 16]`. A global
  row has project_id 0, version `FORMAT_VERSION` = 1, user_id 0 (single seat). Every generated id in the
  DB copy is exactly that (colors, wires, housings: project 0, version 1, user 0, timestamps near
  1.79e18 ns).
- Project filtering is a BYTE-RANGE SCAN on the first 3 bytes of `id` (`pjt_bases._project_id_bounds`;
  there is no real `project_id` column). So the leading 3 bytes mean "which project", and 0 means global.
- The all-ones UUID decodes as project 16,777,215, version 15, user 65,535 -- it sits inside that project's
  scan range and is not a global id. WITHDRAWN.
- The layout-correct choice: project 0, version 1, user 0, and a small fixed timestamp, e.g. timestamp 1 =
  `00000000000000000000010000010000` (what `pack_global_row_id(1, 0)` returns). A real id's timestamp is
  `time.time_ns()` (about 1.79e18) and is bumped forward on ties, so it can never reach 1, and the
  MySQL `next_global_row_id()` is time-based too (its body not read). No row in the DB copy uses it
  anywhere (checked every `id` and `*_id` column). NIL itself is the one id outside the layout
  (version 0), which is how it has always been.
- NIL is THE "unset" sentinel app-wide: it is in 614,839 id/FK cells of the DB copy, ~20 `create_database`
  lookup modules return it for a missing name, and `global_db/mixins/base.py NIL_ID` makes mixins return
  None for it. A second "unset" id for colours is therefore a deliberate exception to that convention.
- Existing code that ALREADY treats a nil COLOUR as "no colour": `Wire.stripe_color`
  (`global_db/wire.py`), `ui/editor_db/wire.py` and `ui/pegboard_table/wire_table.py` (the list icon
  builders: nil colour -> no icon), and `ui/editor_circuit/editor_widget.py` `_unset`. Because the nil row is
  Black, a wire that is truly black (stored as nil) is shown there as having no colour. Each of those
  places needs a look when the new id is introduced.
- Not checked: the MySQL stored functions and the sibling repo's `builder/id_generator.py` bodies, and
  whether anything else decodes ids (only `PJTEntryBase.project_id` and `AppUsersTable.insert` call the
  `unpack_*` helpers in this repo).

## 3. Data facts (measured 2026-11-03 on a copy of the live `harness_designer.db`)

- 90,997 wires: 32,474 with 1 conductor, 58,523 with 2 or more (2: 5,537; 3: 5,744; 4: 6,141; up to 120).
- `wire_types`: Wire 71,251; Ribbon 19,736; Coaxial 10. Ribbon rows are multi-conductor too.
- 35,860 multi-conductor wires are shielded.
- `wire_size_dia` MEANING (checked 2026-11-03 after the user doubted it; my first note called it
  "per-conductor size" without checking). Against the other size columns, over the rows that have it:
  - `wire_size_cross` equals the bare AWG area exactly (ratio 1.00) on every multi-conductor row, and
    `wire_size_dia` / bare-AWG-diameter is 1.00 to 1.32, set by `strands`: 1 strand 1.00, 7 about 1.18,
    19 about 1.19, 37 about 1.08, 133 about 1.27, 200 about 1.31. So it is ONE conductor's metal
    (stranded envelope) diameter, not the cable and not the insulated conductor.
  - It cannot be the cable: dia / `od_mm` is at most 0.48 on every multi-conductor row (median 0.25 for
    pairs, 0.19 for 3 to 8), and a pair's `od_mm` is about 2.05 x (2 x dia) at the median.
  - Single-conductor wires follow the same pattern; 37 of them have `od_mm` < dia (bad `od_mm`, e.g.
    0.03 mm on 'CAT-82A-TC-T-26').
  - Rows with 9 or more conductors (ribbon) have dia = bare AWG exactly and no `od_mm` at all.
  - AWG is stored negative for 0/00 sizes (-2 is 2/0, e.g. 'M22759/16--2-0').
  - The catalog has ONE size per wire, so every conductor of a cable is assumed identical; the new table is
    what lets them differ. Insulated conductor OD is not stored anywhere (needs `wire_size_dia` plus a wall).
- ZERO multi-conductor wires have a `stripe_color_id`, so the source data has no per-conductor colour or
  stripe at all. The new table is empty until the sibling `harness_designer_database` repo (which builds
  the global parts DB) or a rule fills it. A MIL-STD-681-style colour-by-index rule is the obvious fallback.
- `tpi`: 19,110 wires have tpi > 0 (0.8 to 4.0), 9,590 fractional.
- BUG to fix with this work: `Wire.tpi` in `database/global_db/wire.py` is hinted `int` over a FLOAT column.

## 4. Implementation checklist (when approved)

1. `database/create_database/wire_conductors.py` (plural-name DDL file, model on `deratings.py`, `add_indexes`).
2. `database/global_db/` facade class + registration in `global_db/bases.py` (model on `DeratingsTable`),
   and a mixin on `Wire` exposing the conductors (check existing mixins first).
3. Mirror in the sibling `harness_designer_database` repo (`builder/create_database/`,
   `TABLE_MODULES` in `builder/build_database.py`); keep the two aligned.
4. Update `create_database/MAP.md`, `global_db/MAP.md`, and the repo-root `MEMORY.md` pointer.
5. No migration (MEMORY.md: no backwards compat pre-release); an old dev DB just gets the table created at start.
6. `git add` every new file.

## 5. Rendering design (settled in conversation, not built)

- Today: one straight unit cylinder per path segment (`objects_3d/wire.py` `_segment_transforms` / `render`).
- Draw the twist only when `tpi > 0` and the cable has no jacket (section 2a: "no color"; the old rule
  was unshielded with 2 or 3 conductors); otherwise a jacketed plain tube.
  Lay length = 25.4 / tpi mm. Pair: conductor dia = OD/2, centres OD/4 from the axis, 180 deg apart.
  Triple: conductor dia = OD/2.155, 120 deg apart.
- Procedural vertex shader (GLSL 330 core): vertices come from `gl_VertexID` (ring k, side j) with a static
  index buffer; uniforms = profile circles (x, y, r), `twistPerMm`, `phase0`, plus the existing position /
  rotation / scale(length). Rotation theta(z) = phase0 + 2 pi tpi/25.4 z; normals analytic. New `Program`
  subclass in `gl/shaders/program.py`; reuse `geometry.geom` and `fragment.frag`. One draw per conductor
  so `material.set` can colour each. The CPU keeps the straight cylinder for pick / OBB / hit tests; the
  ray tracer needs a numpy-built mesh. Edge and vertex debug programs need twins.
- Stripes: pin the stripe to profile vertices; the rigid twist carries it as a helix for free. Send a
  per-vertex angular distance to the stripe centre (one extra float through `geometry.geom`); the fragment
  shader thresholds / smoothsteps it and blends two uniform material sets (base, stripe) before lighting.
  Stripe colour == base colour (or NIL) means no stripe. Off when selected.
- Bends (verified numerically in a scratch script, 2000 random bends 5-150 deg incl. near-vertical):
  - Phase carry: `phase0_2 = theta_end_1 + delta`, delta = signed angle about d2 from the segment's own
    x-axis to the parallel-transported x-axis of segment 1 (Q = minimal rotation d1 -> d2).
  - Mitre: end ring shifted along the axis by `t_end = -(p . d_next) / (1 + d . d_next)` (start ring uses
    the previous direction), `|t|` max = r_outer tan(beta/2). Both rings then land on the bisector plane.
  - Seam error: both 6e-13 mm; no carry about 2 mm; no mitre about 1.9 mm.
  - Taper: fade the shift in over a distance longer than |t| so rings do not cross
    (`z' = z + t clamp((z-(L-D))/D, 0, 1)`); NOT numerically verified.
  - Caveats: sharp bends (about 120-150 deg and up), short segments, beta = 180, the +/-Z singularity of
    `_rotation_from_direction` (handled by the carry), faint normal crease at the seam, reduce `phase0`
    mod 2 pi on the CPU, all of it is CPU scalar bookkeeping on geometry change, not per frame.
  - Per-segment uniforms: position, rotation, length, `twistPerMm`, `phase0`, previous/next direction in
    local coordinates (+ flag when absent), taper length.
- Smooth bends (2026-11-07): a rigid mitre at a sharp waypoint distorts the conductors (the ring shift and its fade grow with
  `tan(bend / 2)`), so a twisted cable's corners are rounded before `plan` runs: `shapes/twisted_wire.round_bends` swaps each
  corner for a tangent arc of chords (10 degrees apiece, radius 4 cable diameters, tighter where a segment is too short to hold it),
  and the mitre then only closes the gap between chords. Checked numerically over 2000 random 5-150 degree bends (pieces meet to
  1e-13 mm, end directions unchanged, no turn between neighbours over 10 degrees); NOT run in the app. Picking / OBBs still use
  the unrounded straight segments. The 4-diameter radius is a constant (`BEND_RADIUS_DIAMETERS`), not a setting.
- Bundle ends: per-wire entry/exit offsets derived at render time as `entry_w = P_end + frame * offset_w`;
  wires stay bound to the shared Point and `_segments` (`objects/mixins/wire.py`) is the override point.

## 6. Open decisions

- Final column list for the conductors table (section 2).
- Which conductor gets a stripe and where on it; lay direction (S or Z; the data has none).
- Where per-conductor colours come from (new data vs a by-index rule). For ribbon cable the makers give only
  one colour, so it is a rule: all conductors in the cable colour, conductor 1 with a stripe (usually red) or the
  rainbow, chosen by something the user decides (a part number option, or a property on the wire).
- Pictures for ribbon cable, wire-type and flexible-PCB (section 7, a TODO: no layers or classes yet).
- Fan-out of a multi-conductor cable at its ends (section 8, a TODO: new project table, end layouts, order dialog).
- Samples-per-turn / LOD policy; ray-tracer representation; sharp-bend fallback; the hidden stretches
  inside bundles (`_hidden_waypoint_ids`).

## 7. Ribbon cables (added 2026-11-04, design only, nothing built)

What the data has today (measured 2026-11-04 on the database repo's JSON):

- `wire_types` already has `Ribbon` (id 2). 19,736 wires use it: all Molex Premo-Flex FFC / RFC / FPC jumpers
  (flat laminated strips, contacts on one or both sides, types A to D). `num_conductors` is right on them, but
  there is no size, colour or `od_mm`. The pitch (0.25 to 2.54 mm) is only in the description text.
- TE: the 5 rows found by searching "ribbon" / "flat" (4 Madison Cable, 20 / 30 / 40 / 50 conductors, and
  `5-1474644-4`, 9 conductors, 24 AWG, 2.54 mm centreline) were imported with `num_conductors` = 1, `od_mm` 0 and no
  wire type. The real conductor count is only in the description. These are the discrete insulated-conductor kind.
- Universal (the generator): none.
- The schema has no pitch and nothing that says "flat", and `wires.od_mm` cannot describe a strip.

Two different constructions, and they need different data:

1. Discrete ribbon (IDC cable): N insulated round conductors side by side, bonded in a web. Each conductor has a
   colour, so it needs `wire_conductors` rows: gray with a stripe on conductor 1 (pin 1), or "rainbow" (the ten
   MIL-STD-681 colours, brown to white, repeating every 10).
   The makers give no per-conductor colours, so the colours come from a rule by index (see section 6).
2. Laminated FFC / FPC (user, 2026-11-04: not supported yet, flexible-PCB style cables come later; the first target
   is the plain ribbon cable of old hard drives): flat copper strips inside a film. No per-conductor colour, so NO `wire_conductors` rows
   (19,736 wires x about 20 conductors of identical rows would add nothing). The renderer draws one flat strip from
   `num_conductors` and the pitch.

   So conductor rows stay optional: no rows means "draw from the wire row alone".

How the makers describe a ribbon cable (researched 2026-11-04; the user's guess was that each conductor's od_mm is
given, and it is NOT):

- TE datasheet for Madison Cable 4-1437373-4 (9 conductors, read from the PDF): "Ribbon & Flat Cable Centerline" 1.27 mm,
  "Cable Insulation Width" 11.43 mm, "Cable Insulation Height" 0.91 mm, "Number of Strands" 7, "Strand Size" 36 AWG,
  "Wire Size" 0.08 mm2 (28 AWG), "Number of Ribbon & Flat Cable Conductors" 9, Jacket Color Gray, Conductor Insulation
  Color Gray, UL AWM 20267, 300 V, 4.4 ns/m, 81 pF/m, 63 ohm. No per-conductor outside diameter and no stripe or
  rainbow colour information.
- 3M 3365 (distributor listings, not the 3M datasheet, which could not be fetched): 28 AWG 7/36 tinned copper,
  1.27 mm pitch, 6-way width 7.62 mm, 8-way 10.16 mm, 28-way ribbon width 35.55 mm and thickness 0.89 mm.
- Amphenol Spectra-Strip (distributor listings): pitches 0.635, 0.89, 1.0 and 1.27 mm, 7/36 or 7/34 strands, an
  overall width, no thickness. The widths are not all n x pitch (34-way at 1.27 mm is listed as 41.91 mm = 33 x 1.27),
  so the maker's width has to be stored where it is given, not derived.
- So what is published is: conductor count, pitch (centreline), overall width, overall thickness (height), the bare
  wire size and strands, and one cable colour. TE and 3M widths equal n x pitch.

What the data holds for the same part: the scraper never reads those labels. `scrapers/te/wires.py` only looks for
"Number of Conductors" (the ribbon label is "Number of Ribbon & Flat Cable Conductors"), and its test
`if num_conductors: continue` starts from `num_conductors = 1`, so that branch can never run: ALL 2,432 TE wires have
`num_conductors` = 1, not only the ribbons. 4-1437373-4 is not in `TE/wires.json` at all; only 5 TE ribbon parts are.

Proposed data change (needs the user's OK): three float columns on `wires`, `pitch_mm`, `width_mm`, `thickness_mm`
(0 = not a flat cable; all three are values the makers publish), in both repos' DDL and the app's `Wire` cache class.
A flat cable is a row with `wire_type` = Ribbon and a non-zero `pitch_mm`. The insulated conductor's outside diameter
(for the round conductors inside the web) is about `thickness_mm`, which `wire_conductors.od_mm` can hold. Strip width
comes from `width_mm`, or n x `pitch_mm` when it is 0. The Molex FFC / FPC jumpers are typed Ribbon too but are a
different product (flexible printed cable, to be added later); they would keep `pitch_mm` = 0 until then, or get
their own wire type, so they are not drawn as discrete ribbon.

TODO: ribbon cable IMAGES (user, 2026-11-04, not started). The layered preview images (status block in section 0,
`image/wire_images.py`) cover single wires, twisted pairs and triples, jacketed and shielded cables and coax. They do NOT
cover ribbon cable, so `database/global_db/wire_image.py` `build_wire_image` returns `None` for the Ribbon wire type and
every ribbon shows `images.no_image`. Both kinds still need pictures:

- Standard wire-type ribbon cable (the IDC kind, the old hard-drive cable): N insulated round conductors side by side in a
  flat web, with a pin-1 stripe or a rainbow, stripped at the end so the individual conductors show. The conductor count
  runs from a few to 60+, so it cannot have one layer per conductor like the twisted pair (`twisted2_*`, `twisted3_*`):
  the layers will have to be made from a repeated conductor strip, and only part of a wide cable can be drawn (with a
  break mark or a fixed number of conductors, to be decided). The picture is keyed by LOOK like the others (conductor
  colours / rainbow or stripe rule, jacket), so the cache key must not include the conductor count unless the drawing
  changes with it.
- Flexible PCB style cable (FFC / FPC, the Molex Premo-Flex rows): a flat film with the copper contacts at the ends,
  contact side A to D, and stiffeners. A separate layer set from the wire-type ribbon.
- Both need the data decisions of this section first (the pitch, width and thickness columns, and where the per-conductor
  colours of a ribbon come from), and the way the cable is drawn in 3D (roll angle, in-plane bends) is the rendering
  design below. Generator: add the new layers to `diagnostics/make_wire_layers.py`; assembly: new `Image` subclasses in
  `image/wire_images.py` with the same look-keyed metaclass cache, then a branch in `build_wire_image` in place of the
  current `return None`.
- Canvas and icon size (user, 2026-11-04): the 400 x 100 canvas of the wire pictures is NOT fixed. A ribbon picture may be
  up to 400 x 400, so that it fits the square 64 x 64 list icon with the right aspect instead of being a thin strip in a
  mostly empty square (a 400 x 100 picture is only 64 x 16 inside the 64 x 64 icon). Because each kind of cable is its own
  `Image` subclass, the icon can be made differently per class: prefer a method the class overrides (a default one on the
  base, a ribbon class that overrides it) over an `isinstance` test inside `build_wire_icon`. Things that assume 400 x 100
  today and must be looked at when a class has another size: `wire_images.py` (`_WIDTH`, `_HEIGHT`, `_place`, the layout
  numbers, all private to the existing classes, so a ribbon class needs its own); `database/global_db/wire_image.py`
  `build_wire_icon` (fits the picture into the box with `resize_keep_aspect`, so it already copes with another shape;
  the shared icon is keyed by picture and size); the circuit editor's `_qimage` (also `resize_keep_aspect`, fine); and
  `objects/bom.py` `resolve_wire_icon`, which STRETCHES the picture to 100 x 25 with `Image.resize` and would squash a
  square picture, so it needs `resize_keep_aspect` (or a per-class size) first.

Rendering, built on section 5:

- One shader for both. A cable is a cross-section layout (a centre and a radius per conductor) plus a twist rate.
  Pair / triple: circles around the axis, twist > 0. Ribbon: circles in a row at x = (i - (n - 1) / 2) x pitch, twist 0.
  FFC: one rounded flat box, twist 0. Per-conductor colour and stripe work as for twisted wires.
- New for flat cables: ORIENTATION. A round cable looks the same from every side, a flat one does not, so each
  segment needs a roll angle for its flat. Take the roll from the same parallel-transport frame as the phase carry
  of section 5 (a ribbon is just twist rate 0 with a fixed roll), and let the user set or flip it on the wire.
  Whether the path objects already hold an orientation to hang this on has NOT been checked.
- Bends: a flat cable bends cleanly only about its thin axis. Turning it within its own plane would stretch the
  outer edge; real cables are folded at a 45 degree crease for that. First version: smooth bends about the thin axis
  only, and a warning on an in-plane turn. A drawn crease is an open question.
- Pin 1 is conductor `idx` 0 and must be visible (the stripe), so the strip's roll decides which edge it is on.
- Not checked: how a circuit attaches to ONE conductor of a multi-conductor wire in the app today. Ribbons make
  that matter most, because every conductor goes to a different pin.

## 8. TODO: splitting a multi-conductor cable into its wires (fan-out) (user, 2026-11-04, NOT worked out)

The user's description, which still has to be designed properly ("it is going to be tricky"):

- A twisted pair / triple, or any multi-conductor cable, has to be split into its individual wires wherever its
  conductors connect to terminals or splices. Each conductor then goes to a different place.
- That needs a LAYOUT at each end of the cable, so the app has to track where the ends of the individual conductors
  actually are (where the jacket or twist stops, and where each conductor leaves, in 3D).
- It needs a NEW PROJECT TABLE to hold the data for multi-conductor wires. It belongs to the project, not the
  global catalog, because it is a per-project choice (it is not part of a wire's part data).
- A DIALOG for multi-conductor cables, where the user sets the ORDER in which the wires are fanned out.

Questions to settle before building (none of this has been looked at in the code yet):

- What the project table holds: probably one row per cable end per conductor (cable instance, end, `wire_conductors`
  idx, fan-out position / order, how far the split starts from the end, an offset or direction for the breakout), and
  how it is keyed so a project's rows are found by the project id prefix of the row id (see section 2).
- How a circuit attaches to ONE conductor of a cable today, and to which end object a terminal or splice connects
  (flagged as unchecked in section 7).
- How the split end is drawn: the twist stopping and the single wires leaving in the chosen order, which ties into
  the bundle-end offsets in section 5 and the mitre / phase carry at the cable's last segment.
- What the dialog edits and where it opens from (the cable, the cable's end, a circuit) and what the default order is
  (the `wire_conductors.idx` order is the obvious default).
- Ribbon cable: each conductor goes to a different pin, so it is the same problem at a larger scale (section 7), and
  it may need its own layout rather than a fan-out.
- What happens to the stored layout when the cable is rerouted or its length changes.

### 8a. What the code does today (read 2026-11-05) and the two ways to split

Facts (from `pjt_circuit.py`'s `_walk_circuit` / `connected_members`, `pjt_wire_path.py`):

- A circuit is junctions (terminal: 1 connection point `attach_point3d_id`; splice: 3; service loop: 2) joined by
  wires. A wire is ONE edge between the junctions that own its `start_point3d_id` and `stop_point3d_id`. So a
  multi-conductor cable placed today is one edge: one circuit, one resistance, one current, one temperature, and
  it can only land on one terminal or splice at each end.
- Electrically every conductor is its own wire (own circuit, own current). The cable is a physical thing around
  them.
- `pjt_wire_paths` rows already carry optional tags (`bundle_id`, `concentric_id`, `transition_id`,
  `transition_branch_id`) that mark a stretch of a route as belonging to a shared structure, and rows reference
  SHARED point rows.

Option A: the cable stays ONE `pjt_wires` row; a new project table holds one row per conductor per cable
(its own two end points, split distance, order). The conductor becomes a fifth circuit member type next to wire,
splice, terminal and service loop. Touches `_walk_circuit`, `PJTCircuit` members / `add_member` / `adopt`, the
solver input, the circuit editor, the peg-board wire table, the BOM and the schematic.

Option B (recommended): one real `pjt_wires` row per conductor (new columns `cable_id`, `conductor_idx`, and a
per-end order), plus a small cable row (part, per-end split distance). The conductors share the cable's trunk
waypoints (shared point rows, tagged `cable_id` in `pjt_wire_paths`, like a bundle tag); each conductor's own
route continues past the split to its terminal or splice. Circuits, the solver, resistance, length, BOM and the
cut list all keep working per wire, unchanged. The twisted tube is drawn once for the cable between the two
split planes; each conductor's lead is an ordinary wire route starting at that conductor's helix position at the
split (the profile circle and phase at that z, which `shapes/twisted_wire.py` already computes).
Costs of B: select / move / delete of a cable have to act on the group; a conductor wire's part data has to read
through the `wire_conductors` row (colour, size, `resistance_1km`, `od_mm`) and 1/N of the cable's weight; bundle
and concentric diameter sums must count the cable's OD once, not N times.

How it is started (user, 2026-11-05): a right-click menu entry when the right click happens at the FREE end of the
cable. The machinery for "which end, and is it free" already exists: `WireMenu.__init__`
(`objects_3d/wire.py`) calls `pick_free_end(mainframe, wire, click_pos)` (`handlers/wire_drag_base.py`; None when both
ends are anchored, else the free end, the one nearer the click when both are free) and tests `start_sibling` /
`stop_sibling is None` for "Add Terminal". The new entry ("Split Conductors") sits beside "Add Terminal", enabled when
the part has 2 or more `wire_conductors` rows and that end is free. The peg-board and schematic `WireMenu` classes
have the same shape. So the split happens on demand, only at an end nothing is attached to, so there is never a
circuit to rewire at that end.

Consequences for option B: the first split turns the single wire into N conductor wires. To keep them electrically
independent at the end that is not split yet, each conductor gets its own end point there, a clone that follows the
cable's end point (the existing `parent_point_id` clone mechanism of `pjt_points3d`), drawn on top of each other; if
they shared one point, the walk and `PJTCircuitsTable.propagate` would put every conductor in one circuit as soon as
anything attached there.

USER DECISION (2026-11-05): neither A nor B as written above; a variant of A with two new project tables.
- `pjt_cables`: the placed cable. Largely mimics `pjt_wires` (position, route, visibility, name, notes, smooth, part);
  the user suggested the row class could subclass `PJTWire`. It is the container that is drawn (twisted trunk, jacket)
  and the one BOM / cut-list line, so cable length, weight and OD are counted once (the costs listed for B go away).
- `pjt_cable_conductors`: one row per conductor of a cable. Holds the positioning of the split ends and the like,
  and the circuit id, so the conductor is what a circuit contains (not the cable).
- Started by the right-click "Split Conductors" at a free end (above).

Points raised against it before building (answers pending):
- A conductor row that holds a circuit id also needs resistance, load, temperature, length, and a lead route from
  the split to the terminal or splice (waypoints the user can drag, snapping, "Add Terminal"). That is a wire in all
  but name; `pjt_wire_paths` is keyed on `wire_id`, and the drag, snap, routing and layout code is written for wires.
- `PJTCircuit` hard-wires four member types (wire, service loop, splice, terminal: `pjt_circuit.py` is 1,936 lines,
  `_walk_circuit` / `connected_members` / `_prepare_solve` / `adopt` / `members_changed` / the control all list them),
  so the conductor is a fifth.
- If `pjt_cables` subclasses `PJTWire` it inherits `circuit_id`, `resistance`, `load`, `operating_temp`, `part_data()`
  that mean nothing for a cable and must be switched off, and every `isinstance(..., PJTWire)` will accept a cable.
  Possibly the shared part (route, position, visibility) should be factored out instead.
- A conductor's resistance / length = lead at one end + the cable's trunk length + lead at the other end.
- Which parts become cables (conductor rows exist), and no migration of existing projects (pre-release rule).

USER DECISIONS, continued (2026-11-05):
- `pjt_cable_conductors` row class subclasses `PJTWire` (a conductor is wire-like: circuit id, lead route, snapping).
- It needs TWO waypoint lists, one per end, because both ends of a cable can be split and each conductor lands on
  its own terminal or splice at each end. Proposed: the conductor's route is only its two LEADS (end point ->
  waypoints -> split point at that end), each lead tagged start / stop in `pjt_wire_paths`; the trunk between the two
  split points belongs to the cable. An end that is not split has an empty lead (split point == end point).
- Shielding is a conductor too. A shielded cable such as coax keeps `num_conductors` = 1 (correct) but has an extra
  SHIELD conductor that can be broken out and connected. Proposed: a kind column on `wire_conductors` (conductor /
  shield, later drain) with the builder emitting the shield row (no-None-guards rule: fix the data), and
  `WireConductorMixin.is_twisted` counting only kind = conductor rows against `num_conductors`. USER RULE
  (2026-11-05): ANY wire with shielding becomes a cable, whatever its conductor count; so a part is a cable when
  `shielded` or `num_conductors` > 1, and a plain unshielded single-conductor wire stays a `pjt_wires` wire. The test is the `shielded` flag, not the wire
  type: a coax part with `shielded` false stays a wire (user, 2026-11-05). In the builder's JSON that is 3 Molex coax
  parts (shielded 7, unshielded 3); all 26 TE coax parts are shielded.
  Measured on the builder's JSON the same day: 23,319 of the ~26,800 wires are cables by this rule (Molex 20,310,
  TE 3,016), 1,602 of them shielded (Molex 1,469, TE 133), and conductor rows exist only for TE's 365 (Molex has no
  `wire_conductors.json`; its 4 to 40 conductor cables are ribbon / flat). So the cable test cannot depend on conductor
  rows existing: they have to be written for every cable (builder, by the by-index rule of section 6 / 7) or made when
  the cable is placed.
- Open: pegboard rope pull and slack (`rope_pull.solve_chain` is stateless per chain: two anchors + required length;
  a conductor would be three chains, lead / trunk / lead, meeting at split points shared with N other leads), and the
  schematic view (precedent: bundles are never shown in the schematic; proposal: the cable is not in the schematic and
  each conductor is drawn as its own terminal-to-terminal wire with ONE ordinary waypoint list there, so the two-list
  route is a 3D and peg-board concern only).

USER DECISIONS, continued (2026-11-05, later):
- NO separate catalog row for a shield (this replaces the proposed `kind` column on `wire_conductors`). The catalog's
  `wire_conductors` keeps real conductors only. `pjt_cable_conductors` gets a column that says the row is the
  shielding, so a shielded cable has its conductors plus one shield row in the PROJECT table, made when the cable is
  placed. `is_twisted` is therefore unchanged (it counts catalog conductor rows against `num_conductors`).
- Every conductor MUST be describable: its own size (dia / cross / AWG) must be available. Where the catalog has no
  individual colour for a conductor its colour is WHITE and the user updates it. So catalog conductor rows are
  needed for every cable (builder: copy the cable's size into each row, colour white where unknown; TE's existing 365
  keep their colours). This takes the "builder writes the rows" side of the open question.
- The object explorer (`ui/object_browser/objectbrowser.py`) and the object editor (`ui/editor_obj`, the per-table
  `_control` singletons) must handle cables and their conductors:
  - Explorer: a Cables category (as Wires is) whose node lists its conductors and the shield; each conductor is also
    listed in its circuit's membership group (circuit rebuild is driven by the row's `'members'` tag) and as a
    cross-reference under the terminal / splice it lands on. Items are weakref-pruned and `reset()` rebuilds, as
    for every other type.
  - Editor: a `PJTCableControl` (name, notes, part, trunk length, split distance and fan-out order per end,
    visibility) and a `PJTCableConductorControl` (name, colour, stripe, size, shield flag, circuit through
    `PJTCircuitControl`, electrical page like a wire's, lead end points). Each table's `_control` is a class-level
    singleton that must be cleared with `set_obj(None)` on detach (see `project_db/MAP.md`).

USER DECISION (2026-11-05, ribbon): ribbon cables are cables too and go through the same cable / conductor tables and
the same split, but they are NOT twisted and have no single jacket round the conductors; they are rendered
differently. So the cable needs a STYLE, derived from the part (never stored, like `is_twisted`):
- TWISTED: `tpi` > 0, "no color" jacket, 2 or more conductors (today's `is_twisted`).
- RIBBON: wire type Ribbon (discrete IDC ribbon; laminated FFC / FPC come later, section 7).
- JACKETED: every other cable (shielded, coax, round multi-conductor).
The style decides the trunk's drawing (twisted tubes / flat strip of conductors in a row / one tube), how a split looks
(a ribbon's conductors tear off the web in pin order, so the fan-out order is positional there and free for the others),
the editor pages (pitch, roll for a ribbon) and the picture. It cannot come from `wire_type` alone: TE has no wire type on
all but 32 of its 6,491 wires (TE's 2,853 twisted cables have type None).
Measured the same day: 525,000 catalog conductor rows would be needed to give every Molex cable one (19,734 of 20,310
are Ribbon, up to 120 conductors) against 6,300 for TE, and only 1,176 Molex ribbons have a wire size at all, none an
`od_mm`. Proposal that meets "each conductor describable, sizes available, white if no colour": the builder writes
`wire_conductors` only where the maker gives per-conductor data (TE), and the PROJECT conductor rows are made when the
cable is placed from the cable row (size copied; colour white; ribbon pin-1 / rainbow rule when chosen). Needs the user's OK.
USER DECISION (2026-11-05, answer): NOT that. The DATABASE BUILDER makes the conductors: `wire_conductors` rows for every
cable (TE's own data where it exists; otherwise the cable row's size and colour white, ribbon by its pin-1 / rainbow
rule). The 525,000 Molex rows are accepted; measure the catalog size after the first build. The placed cable copies its
conductor rows into `pjt_cable_conductors`, and the user fixes a white default colour (or a size) in the OBJECT EDITOR,
per placed cable, which is why the editor must handle multi-conductor cables (`PJTCableControl`,
`PJTCableConductorControl`).

Proposed build order (nothing started): 1 builder writes the conductor rows; 2 app: `CableStyle` property, the
`pjt_cables` and `pjt_cable_conductors` tables and row classes; 3 placement makes a cable with its conductor rows;
4 trunk rendering by style (twisted done; ribbon, jacketed); 5 "Split Conductors" and the two-list leads; 6 conductors
as circuit members; 7 object explorer and editor; 8 peg board (rope pull, slack) and schematic.

BUILT 2026-11-05, step 1 (database repo, `builder/create_database/wire_conductors.py`, uncommitted): `add_records` now
gives every cable the files do not describe `max(1, num_conductors)` default rows (the cable's size, strands, core
material, insulation material and resistance; colour White; no stripe; `od_mm` 0), and no longer returns early when
there are no files. Checked on a test build on D: (exit 0, no warnings): every cable has rows, no non-cable has any, and
each cable's row count equals `max(1, num_conductors)`. Real totals (the earlier 23,319 counted only the manufacturer
JSON; the Universal generated military cables are cables too): 113,768 cables of 148,048 wires; 305,486 described rows
(88,036 cables: TE twisted and Universal) plus 533,202 default rows (25,732 cables: Molex 20,310, TE 3,016 and the
rest) = 838,688 rows; test database 394 MB; `row_ids.txt` grows by 533,202 lines (about 19 MB, 26 to 45 MB), which the
real build must commit. The app's `create_database/wire_conductors.py` needs no change (same DDL).

BUILT 2026-11-05, step 2 (app repo, uncommitted, new files `git add`ed): `CableStyle`, `is_cable` and `cable_style` on
`WireConductorMixin`; the schemas `create_database/cables.py` (`pjt_cables`) and `create_database/cable_conductors.py`
(`pjt_cable_conductors`, every `pjt_wires` column plus the conductor columns); `project_db/pjt_cable.py` (`PJTCable`,
`PJTCablesTable`) and `project_db/pjt_cable_conductor.py` (`PJTCableConductor(PJTWire)`, `PJTCableConductorsTable(PJTWiresTable)`),
registered in `PJTTables` (`pjt_cables_table`, `pjt_cable_conductors_table`). The cable has no 2D columns and no circuit; the
conductor has the whole wire. Decisions made while building: the conductor table is a column-for-column superset of
`pjt_wires` so the inherited `PJTWire` code finds the columns it reads; (a cable's route was first meant to go in
`pjt_wire_paths` under its own id; step 3 moved it to `pjt_cable_paths`, see below); `PJTCable.get_object` / `set_object` wait
for the object layer. Checked on a scratch SQLite with a stand-in for `PJTTables` (insert, read, setters, ordering,
`_resistance_over`, cascade delete, nine `cable_style` cases) and by the schema walk (`pjt_cables` before
`pjt_cable_conductors`); `cython_hint_audit.py` found nothing in the new files. NOT run: the app, a real project database,
the catalog rebuilt with step 1's rows (so `cable_style` has only been run on stand-in parts). Still open from this step:
`length_mm` / weights of a conductor (two leads plus the trunk), conductors as circuit members (step 6), the object editor and
explorer (step 7), the dual lead lists (step 5).

CHANGE 2026-11-05 (user: "if it's twisted and unsheathed then it should be rendered no matter how many conductors"): the 2-or-3
limit is gone. The catalogue has about 3,000 unjacketed parts with a twist rate and 4 to 8 conductors that were drawn as a plain
tube; `is_twisted` now takes any count of 2 or more. `shapes.twisted_wire.profile` packs any number of equal conductors: up to 5 on one
ring; from 6 conductor 0 is the centre one and the rest go round it on one ring while that is 9 or fewer, else in layers as a stranded
cable (layer k at 2kr, up to floor(pi / asin(1 / 2k)) each, innermost first, a part-filled layer evenly spaced). The vertex shader's
stripe centre falls back to +X for a conductor on the axis. Checked: no overlap and the exact outer diameter for 2 to 60, 80 and 120
conductors; offscreen renders of 6, 8, 12 and 19 conductors. Draw cost grows with the count (one tube per conductor per segment).
The icon (`wire_images`) still shows the first three conductors.

FIX 2026-11-05 (user report: a twisted pair with striped conductors looked misshapen): not the stripe, the conductor size. The
catalogue TPI is a flat 1.0 for most pairs (provisional, see above), so a thick pair such as the 6.3 mm 12 AWG M27500 pair had a lay
of 4 cable diameters, a steep helix whose conductors look swollen and pinched. `shapes.twisted_wire.rate_for` now stretches the
lay to at least `MIN_LAY_DIAMETERS` = 8 cable diameters (a real pair is laid 8 to 16); thin pairs are untouched. Checked on the
offscreen renderer with real catalogue sizes; the 8 is a judgement, one constant to change. The TPI column itself is not changed.

BUILT 2026-11-05, step 3 (app repo, uncommitted, new files `git add`ed; 3D editor only, NOT run in the app): placing a cable in
free space. `objects/cable.py` (`Cable` facade, 3D view only, ends always free), `objects/objects_3d/cable.py` (`Cable(Wire)`:
the 3D wire view reused, so the trunk is drawn as a wire is, twisted included; a ribbon is a plain tube until step 4; menu =
Select, Delete), `add_handlers/editor_3d/cable.py` (the wire's placement session with the attaching taken out),
`objects/project.py` (`_cables`, `add_cable` / `delete_cable` / `get_cable` / `cables`, loaded after the wires),
`ObjectBase.is_cable`, `Wire._start_free_space` hands a cable part (`is_cable`) to `Cable.start_add_cable`, and starting a
cable from a terminal or splice says a cable is not attached itself. Database: `PJTCable.get_object` / `set_object`,
`PJTCableConductorsTable.insert_for_cable` (conductor rows from the catalog part, each conductor's end points children of
the cable's, so they follow it), and `pjt_cable_paths` (`PJTCablePathsTable`, a table of its own for a cable's route:
`pjt_wire_paths` is read by code that looks every id up in `pjt_wires`, e.g. `PJTWireLayout.attached_wires`, the rope pull and
`PJTWirePath.wire`, which a cable's id would break). `PJTPoint3D` / `PJTPointPegboard.is_referenced` count the cable tables.
Decisions: conductors are made when the session FINISHES, not when it starts (the cable's end point is replaced at every
waypoint commit and each conductor's end points are children of it); the wire session got a `_paths_table` hook so the cable
session can answer with its own table. Checked on a scratch SQLite (conductors made, children follow a moved cable end,
route table, `is_referenced`, cascade delete) and by importing the whole object layer; the 3D view, the session and the
loader were never run. DECIDED (user, 2026-11-05): a cable with no outer jacket (twisted, ribbon) gets no waypoint layouts; a jacketed one does.

BUILT 2026-11-05, step 5a (app repo, uncommitted; NOT run in the app): splitting a cable's conductors out at an end, drawing only. The
right-click menu of a cable offers "Split Conductors (start|stop end)" (for the end nearer the click; asks the distance from the end) or
"Join Conductors". `PJTCable.start_split_mm` / `stop_split_mm` are the state (0 = not split). The split plane must lie inside the END
SEGMENT of the trunk (distance at most that segment's length less 2 mm), so no trunk waypoint has to move to a lead; a lead therefore has no
waypoints of its own yet. At a split the trunk is drawn only up to the plane (`Cable._segments` is trimmed, so the twist phase starts / ends
at the plane), each conductor's end point is DETACHED from the cable's end (`PJTPoint3D.detach_from_parent`) and moved to a fan-out place
across the cable's true end (conductor position x 2, a shield below the jacket), and each conductor is drawn as a straight tube from its
helix position at the plane to that point (rate-0 `TwistedTube`, so stripes work); join re-attaches the end points. DECISION: no split point
ROWS yet (`start_split_point3d_id` stays NULL); the lead's start is computed at draw time from the trunk's plan (the helix phase through bends
is only known to the view). They are needed in 5b, when a lead becomes a route of its own: the view's `reload_splits` would then write the
computed positions into them. Checked: the detach / attach rules on a scratch SQLite (a detached end does not follow, a re-attached one
snaps on and follows, a never-live point works) and the maths offscreen (straight pair split at both ends, bent triple, 8 conductors: leads
join the helix conductors without a jump). USER DECISION (2026-11-05, 5b): a conductor's LEADS are ordinary wires. A lead is a `pjt_wires` row with a new nullable column
`cable_conductor_id` (the conductor row), from a free end (where a terminal or splice attaches, as to any wire) to a SPLIT POINT on
the trunk's split plane. `pjt_cable_conductors` is KEPT (not folded into `pjt_wires`): the conductor has to exist before any lead
does (colour, size, shield flag, idx, resistance are edited per conductor, an end that is not split has no lead), and it becomes the
middle of the run, a junction with two connection points (the split points) that the leads attach to, modelled on the wire service
loop (2 connections, a circuit member). This replaces the "conductor row subclasses PJTWire with two waypoint lists" decision:
each lead has its own route, so there is one list per lead. A lead's colour / size / resistance come from its conductor through
`PJTWire.part` -> `project_db/conductor_part.ConductorPart`.
BUILT 2026-11-05, 5b stage 1: the `cable_conductor_id` column, `PJTWire.cable_conductor_id` / `is_cable_lead` / `cable_conductor`,
`PJTWire.part` returning a `ConductorPart` for a lead, `PJTWiresTable.leads_of`; checked on a scratch SQLite (the lead's part answers the
conductor's colour, stripe, size, od, resistance and a share of the weight; an ordinary wire and a conductor row are unchanged; the
link is stored and can be cleared).
BUILT 2026-11-05, 5b stage 2 (NOT run in the app): `Cable.split_end` makes, per conductor, a split point on the plane (`start_split_point3d_id`
/ `stop_split_point3d_id` now used; kept on the plane by `_sync_split_points` when only the distance changes) and the lead wire (end
point -> split point, a `Wire` facade added to the project); `join_end` refuses while a terminal or splice is on a lead's free end
(`can_join`), else deletes the leads and split points and re-attaches the end points; deleting the cable deletes its leads. The 5a
drawing of leads inside the cable view is removed (the leads are drawn as wires). Checked on a scratch SQLite (`leads_of`, the lead's
points, join bookkeeping); the facade, the lead's 3D view reading a `ConductorPart`, and the project loader were never run.
BUILT 2026-11-06, 5b stage 3 (NOT run in the app): `objects/cable_conductor.py` `CableConductor`, a view-less sibling-graph node (like the
service loop: a lead at each cable end). A lead's `stop_sibling` is now its conductor (so "Add Terminal" is no longer offered on the split-plane end,
and `Cable.can_join` is unaffected: it only looks at the free ends). Linked by `Cable.split_end` and rebuilt on a load by
`Project._reconcile_wire_sibling_graph`; `Wire.trace_run` walks through it to the cable's other lead; `wire_circuit._replicate_operating_temp`
labels it. Checked with fakes (the node's bookkeeping, the load reconcile); the facade, the real `Wire.set_sibling` call and the loader were
never run. NOT in stage 3 (the circuit walk, member lists and the trunk in `trace_run` came in stage 4, below): `Wire.is_connected` (needs a Terminal/Splice at both ends,
so a lead is not shown in the schematic).
BUILT 2026-11-06, 5b stage 4 (NOT run in the app): the conductor is a circuit member and a junction. `PJTCircuitsTable.connected_members` and
`PJTCircuit._trace_full` give it two connection points (its split points), so the walk goes terminal -> lead -> conductor -> lead -> terminal and
a circuit crosses a split conductor; `PJTCircuit.cable_conductors` (cached like the other member lists) is in `resistance`, `wire_length_mm`,
`wire_weight_g`, `detach_members`, `merge_from` and `over_temperature_members`. `PJTCableConductor.length_mm` is the TRUNK (the cable's length less
the two splits, along the axis; the helix of a twisted conductor, a percent or two, is not counted), `weight_g` / `weight_lb` the cable's share per
conductor row, so `part_data()` hands the solver the trunk's resistance (the row's own `resistance_1km`) and length; `Wire.trace_run` adds the
trunk. Checked with stand-ins (the walk, `connected_members`, the trunk length / weight / resistance / `part_data`); never run in the app.
NOT done: the circuit editor (`ui/editor_circuit`) and the object browser do not list conductors (they read `circuit.wires` /
`wire_service_loops`), `Circuit.highlight` does not colour the trunk, a conductor in a bundle's heat (`_bundle_component` reads wires only), the
shield as a return path, and `Wire.is_connected` / the schematic look of a split conductor.
BUILT 2026-11-06, lead routing (NOT run in the app): a lead's waypoints already work through the ordinary wire code (right-click Add Handle ->
`WireLayout`, 3D route only); what needed doing was keeping the lead a lead. The conductor's split point is a drag anchor
(`WireDragMixin.is_anchor_point`, so it cannot be dragged off the split plane and is not offered by `pick_free_end`); a lead is neither a wire-end snap
target nor snaps to one (`SnapProbeSet`: wires that meet are merged into one row, which would lose the conductor); the lead's menu disables Add Splice /
Add Wire / Add Wire Service Loop / Add to Wire (they split or branch the row into a wire without `cable_conductor_id`). Still open: a splice or
service loop IN a lead (would need `cable_conductor_id` carried through `wire_topology` and `can_join` / `join_end` to follow the whole lead chain),
a lead in the pegboard / schematic, and the first stretch of a lead leaving the plane along the trunk (a lead is straight until the user adds handles).
BUILT 2026-11-06, fan-out order (NOT run in the app): `start_order` / `stop_order` (per conductor, per end; default `idx`) now decide which fan place a
conductor's end lands in. The places are fixed per cable (one per conductor row: where that row sits in the cable, spread out by `FAN_SPREAD`), so
reordering swaps conductors between places; the shield is just another place (it can be moved off the bottom). Menu: "Fan-out Order (start|stop end)..."
-> `ui/dialogs/fan_out_order.py` (Move Up / Move Down) -> `Cable.set_fan_order`, which moves the end points of a split end at once and only stores the
order of an unsplit one (the first split uses it). Refused while anything is attached to a lead's free end (`can_reorder`, same rule as Join: the
attached terminal would be left behind). Checked with stand-ins and the dialog offscreen; no preview of the fan in the dialog.
BUILT 2026-11-06, step 4 (NOT run in the app; checked offscreen through the real shader and with stand-ins): the trunk by style. TWISTED as before;
RIBBON is a flat strip of touching round conductors in a row (`shapes.twisted_wire.ribbon_profile`; the same shader, rate 0), pin 1 (conductor 0)
on the -X edge, its conductor colours from the part's conductor rows (the cable's colour when it has none); JACKETED is one round tube. The catalogue
gives a ribbon no pitch, width or `od_mm` (section 7's proposed `pitch_mm` / `width_mm` / `thickness_mm` columns were NOT added), so the pitch is a RULE:
the smallest of 0.635 / 1.27 / 2.54 / 5.08 mm that holds the insulated conductor (its `od_mm`, else the bare diameter + 0.5 mm; 28 AWG gives 1.27), the
strip is `count * pitch` wide and one pitch thick, and the web between conductors is not drawn (they touch). `WireConductorMixin.trunk_size` is the one
place that size is worked out (a jacketed part with no `od_mm` gets the diameter that holds its conductors); the 3D view, `ConductorPart` (a ribbon lead is
one pitch wide) and the split dialog read it. ROLL: a flat cable needs an orientation, so `pjt_cables.roll_deg` (new column) turns the strip about its
length at the start of the trunk and every bend carries it on by parallel transport; the view bakes the roll into each segment's angle, so picking and the
selection overlay use the strip's own box. Menu "Roll Ribbon..." (refused while an end is split, as the split points sit on the flat side). The fan-out
order is positional for a ribbon (menu entry disabled). Known: a ribbon turned edgewise (in its own plane) is not warned about or creased (section 7);
the default roll is the 3D view's own frame, not "lying flat"; no web; laminated FFC / FPC, the ribbon picture and a conductor-colour rule (pin-1 stripe /
rainbow) are still open; 120 conductors cost 120 tubes per segment.
REVISED 2026-11-06 (user, after reviewing step 7): the conductor's own values live ONLY in the catalog. `pjt_cable_conductors` keeps NO copy (the colour / stripe /
material / size / od / resistance columns are gone): it holds `conductor_id`, the row of `wire_conductors` it is, and `PJTCableConductor.part` (and a lead's `part`)
returns that catalog `WireConductor`, which is now a real catalog row class that answers the same API as `Wire` (anything it does not define is the cable's, through
`__getattr__`); the shield, which has no catalog row, is a `ShieldConductor` stand-in. `ConductorPart` (project_db) is gone. Editing is done to the part itself, so it is
GLOBAL: in the object editor a conductor (or lead) shows the project wire control, whose Part tab shows the cable's catalog wire, which has a Conductors tab (shown only for a
wire with conductors): a notebook with a tab per conductor and the controls for that `wire_conductors` row (`WireConductorsControl` / `WireConductorControl` in
`global_db/wire.py`). After an edit `Project.reload_cable_looks(wire_id)` redraws every placed cable of the part and its leads. This replaces the "per placed cable copy the
user edits" decision of 2026-11-05 and the `PJTCableConductorControl` / `ConductorColorControl` of the first step 7 (removed). The paragraph below describes the first
version where it speaks of conductor controls and copies; the browser part still stands.
BUILT 2026-11-06, step 7 (NOT run in the app; checked with stand-ins, the controls and the browser panel built offscreen): the object editor and the object
browser handle cables and their conductors. Editor: `PJTCableControl` (name, notes, smooth, position, visibility, the part, and a read-only Info page: length,
weight, conductor count, both split distances, the ribbon roll; a split moves points, so it stays on the right-click menu) and `PJTCableConductorControl`
(name, notes, colour and stripe, size, the trunk's length / weight / resistance, circuit, part). Selecting a cable used to raise `AttributeError` (no `control`
on `PJTCablesTable`). `ConductorColorControl` (new, `project_db/conductor_controls.py`) picks colours by name from the catalog and never edits one. A colour edit
redraws the trunk (its look is now built from the placed cable's conductor rows, the builder's white rows included, the catalog part's only when there are none) and
recolours the leads (`Cable.reload_looks`). Typing one of the three sizes clears the other two (`ConductorPart` reads dia, cross, AWG in that order). Browser: a Cables
category; a cable's item has a Conductors group, one selectable item per conductor (the shield marked) with its circuit and its lead wires, listed again after the
conductors are made, a split, a join and the project load; a circuit lists its Cable Conductors. A conductor has no view, so `CableConductor.set_selected` bypasses the
editors' canvases and tells only the object editor and the browser. A lead's Part page shows the cable's catalog wire. NOT done: a conductor's mention under the terminal /
splice it lands on, the lead end points in the conductor editor (a lead is a wire with its own control), a stripe added or removed (or a changed diameter) on an existing lead
without remaking it, the fan-out order and split distance as editor fields (menu only), a conductor in the circuit editor dock (`ui/editor_circuit`), selecting a conductor in
3D, the BOM / cut list.
BUILT 2026-11-06, step 8 (NOT run in the app; checked on stand-ins and a scratch SQLite: `pegboard_cable_test.py`, `schematic_conductor_test.py`).
USER DECISIONS (2026-11-06): schematic = CONDUCTORS ONLY (no cable, no leads; each conductor one terminal-to-terminal wire with one ordinary waypoint list);
peg board = THE CABLE STRIP PLUS THE LEADS (the cable at its real width with its own board waypoints, the leads ordinary wires on their own board points).
PEG BOARD: `objects_pegboard/cable.py` (a subclass of the peg-board wire view). A cable is placed in 3D and SEEDED onto the board, as a bundle is: the 3D route
is unfolded into the board plane with every segment keeping its real length (`seed_from_3d`), so the cable is exactly as long on the board and the rope pull
and slack do not apply to the trunk (and there is nothing to attach to it). Splitting an end lays the conductors out FLAT: side by side across the trunk at
the split plane, their ends across the cable's true end (the same order as 3D; side by side for a ribbon). Each conductor gets a board split point and a
board end point and its lead's board ends are those; join deletes the split points; the distance and the fan order move them. The lead's length on the board is
the straight line (a little different from 3D: `wire_slack` bows the shorter view once a terminal is attached, as for any wire). Not built: dragging a placed
cable (in 3D either), a board placement session for a cable, the table of wires (`ui/pegboard_table`) listing a cable's conductors, the cable's own rope pull.
SCHEMATIC: `objects/cable_conductor.py` `ConductorRun` + `objects_schematic/cable_conductor.py`. A conductor is drawn while both its leads end on a terminal or
splice: its row's 2D end points are the leads' own (so the line follows the terminals), the router sees the run as a wire (`start_sibling` / `stop_sibling` are
the terminals/splices), and the stored 2D route is the row's own (`pjt_wire_paths` by the conductor's id). `CableConductor.refresh_schematic` is asked when a
lead attaches (`on_wire_attached`), is cut free or deleted, and for every conductor as a project loads. Not built / unknown: dragging an interior waypoint
(a `WireLayout` handle finds its wire through `project.get_wire`, which does not know a conductor), a conductor in Auto Arrange's weights, a splice or service
loop in a lead, the conductors in the circuit editor dock.
BUILT 2026-11-07, split-end markers (user request; NOT run in the app): splitting a cable end draws a PSEUDO layout (not a database row; the split point is already stored) where each conductor's lead meets the trunk, in 3D and on the board. It is sized and coloured as the conductor (not the stripe), is not pickable, and is made again whenever the cable is built and dropped by Join Conductors and when the cable is deleted.
BUILT 2026-11-07, conductors on the board (user report: the board drew a multi-conductor cable as ONE cylinder; NOT run in the app): `objects_pegboard/wire.py` now draws a twisted look the way the 3D view does (it borrows the 3D view's look and drawing methods as class attributes) and `objects_pegboard/cable.py` builds the cable's look (twisted pair / triple, ribbon row, or a plain jacketed tube). A ribbon lies flat on the board with its width across the path.
BUILT 2026-11-07, dragging a placed cable (user request: as a wire is dragged; NOT run in the app): select the cable, then press on it: near a free end drags that end, between two waypoints drags both, and a cable with no waypoints drags whole (the wire's plan, `WireDragMixin.plan_wire_drag`). No snap (a cable's ends are free). The conductors follow: an unsplit end carries them (children); a split end re-lays its split plane and carries the free lead ends that have nothing attached (`Cable.follow_drag`). Dragging in one view leaves the other alone, so the board's length can differ from the 3D length. Not built: bundle routing of a cable, re-orienting fanned-out ends when a waypoint drag turns the end segment, a board length budget.
NEXT: run it in the app (nothing of the cable work has been run); then the open lists above.
Known: the BOM would list a lead's length against the cable's part.
NOT done (older 5b list, now partly superseded): leads as selectable objects (select, drag the end, waypoints, "Add Terminal"),
the fan-out ORDER dialog (order is `idx`; `start_order` / `stop_order` columns exist, unused), the OBB / hit test of a lead, ribbon's
positional fan-out, a split distance beyond the end segment, and the circuit side (step 6). Join does not check whether anything is
attached to a conductor's end (nothing can be yet): when attaching exists it must refuse. KNOWN GAPS: dragging a placed cable's end or waypoint (its `handle_interaction` only selects); a
waypoint marker (`WireLayout`) of a cable is sized as for no wire and `attached_wires` is empty for it; cables are not in the
object browser, the BOM or the cut list; no peg-board view; "Split Conductors" is step 5.

Not checked yet: the add-wire handler and wire snapping, `Wire._segments`, the peg-board and schematic wire
renderers, and how many places count wire rows.
