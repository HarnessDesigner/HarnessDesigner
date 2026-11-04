# Twisted wires and the per-conductor table (design, started 2026-11-03)

Nothing here is built yet. Written down on purpose (MEMORY.md: "write down a detailed verbal spec
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

NOT DONE:
- The row id ledger keeps the numbers of part numbers that no longer exist (they are never reused, and the first
  versions of the M27500 and pair numbers are in it), which is harmless.
- Slash sheets /34, /35, /41, /42, /45, /46 (also /1, /2, /14, /15, which are in MIL-W-22759E's similarity
  groups): no source with the full table was reachable (Glenair returned 403 for them; the distributor pages lack the
  conductor diameter). `MIL-W-22759E.PDF` (the base spec, 43 pages, a bad OCR) holds no per-AWG tables, only the list
  of slash sheets; the Amphenol CIT `M22759.pdf` covers exactly the families the generator already had
  (/5-/12, /16-/23, /28-/31, /80-/92).
- The twisted-wire rendering (sections 5 and 6) is still design only. `Wire.tpi` is still hinted `int`.
- The live `harness_designer.db` has no `wire_conductors` table and old colour ids until it is rebuilt from the builder.

## 1. Goal

Render a multi-conductor wire in 3D as what it really is: a twisted pair/triple (conductors visible, no
jacket) when it is unshielded and has 2 or 3 conductors, otherwise a plain jacketed tube. The twist rate
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
