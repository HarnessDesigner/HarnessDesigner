# Concentric twisting -- plans and notes

Started 2026-10-25. Design lives HERE; add new decisions to the decision log at the bottom, not to
MEMORY.md (MEMORY.md only keeps a pointer to this file). Read this file in full before touching
anything concentric / bundle-packing related.

Related docs: `BUNDLE_DESIGN.md` (bundle spec + code audit), `BUNDLE_PLACEMENT.md` (placement),
`TRANSITION_DESIGN.md` (transitions / branches), and MEMORY.md `### Wire bundle packing requirements`
(the 2026-07-14 requirements baseline, reproduced and extended below).

## 0. Provenance legend

Every rule or number carries a tag so it is obvious how far to trust it:

- **[STD]** read by this project in the primary text of MIL-STD-339(AT) (section 2). Page / table
  references are to that PDF's own page numbers (printed page = PDF page - 8).
- **[TE]** read in the primary text of TE Connectivity code of practice ELE-3COP-256 Rev 6.
- **[HPA]** High Performance Academy (motorsport harness training) -- a secondary, practitioner
  source that itself cites MIL-STD-339 and the TE code of practice.
- **[DERIVED]** derived in this project's research session and checked numerically against [STD].
- **[MEM]** from MEMORY.md -- the user's own earlier research (2026-07-14), not re-verified.
- **[USER]** a decision or requirement stated by the user.
- **[OPEN]** not yet decided / not yet found.

## 1. Goal [USER, 2026-10-25]

Build concentric twisting into the application. The database tables are partly in place. Missing:

1. The code that **calculates the layout** -- which layer each wire is in, how many layers, where
   each wire sits in the cross-section, lay direction / lay length per layer.
2. A **display of the wire layouts** -- there is currently no picture of a bundle's wire layout.
3. The **rules** (MIL spec and any other resources) hammered out first, and the **math behind the
   layer packing** set in code.

## 2. Sources actually read (2026-10-25)

| Tag | Document | Where | Notes |
|---|---|---|---|
| [STD] | **MIL-STD-339(AT)**, "Wiring & Wiring Devices for Combat and Tactical Vehicles, Selection and Installation", 07 Dec 1987 (Notice 1 12-1987). **Cancelled**; its instructional content went into MIL-HDBK-508. | https://everyspec.com/MIL-STD/MIL-STD-0300-0499/MIL-STD-339_17076/ (PDF: `.../download.php?spec=MIL-STD-339.017076.PDF`, 4.7 MB, 150 pp, scanned with an OCR layer) | The relevant part is **Section 600 "Wiring harnesses, molded cable assemblies, hybrid cable assemblies, and convolute tubing cable assemblies"**: paras 600.3.4 - 600.3.10 (printed pp 56-63), **Table XXI** (p 62), **Figure 4** (p 61), **Figure 5** (p 64), **Table XXII** (p 65), glossary 600.6.1.x (pp 83-86). |
| [TE] | **ELE-3COP-256 Rev 6 "Hand Cable Laying"** (TE Connectivity code of practice, 2011) | https://www.te.com/commerce/DocumentDelivery/DDEController?Action=srchrtrv&DocNm=ELE-3COP-256&DocType=SS&DocLang=EN (96 KB PDF; landing page https://www.te.com/en/products/wire-protection-and-management/harness-software-harnware/hand-laying-cables.html) | States it takes preference over IPC/WHMA where they differ. Sister documents: ELE-3COP-257 (binder), ELE-3COP-258 (wrap). Not read yet. |
| [HPA] | High Performance Academy "Concentric Twisting Explained" webinar + two course pages | https://www.hpacademy.com/previous-webinars/293-concentric-twisting-explained/ , https://hpacademy.com/courses/professional-motorsport-wiring-harness-construction/practical-wiring-harness-construction-skills-concentric-twisting | Secondary. Useful for practice (batch size, lacing, branching). |
| -- | MIL-HDBK-508 (successor; 21 Apr 1998, Notice 1 2008 says still valid for acquisition) | https://everyspec.com/MIL-HDBK/MIL-HDBK-0500-0599/MIL_HDBK_508_1828/ | **Not read yet** -- may restate / revise Table XXI. Guidance only, not a requirement. |

**Correction to MEMORY.md (2026-10-25):** MEMORY.md called MIL-STD-339 "Twisting of Wires and
Cables". The standard is the one above (the right document, the wrong title). Section 600 is the
concentric-lay material; Table XXI is "Lay pattern calculations".

Scratch copies of the two PDFs and their extracted text were made in the 2026-10-25 session's
scratchpad (ephemeral). Re-fetch from the URLs above if needed; do not commit the PDFs.

## 3. What already exists in the code (audit, 2026-10-25)

Tables (`database/create_database/`, project-DB wrappers in `database/project_db/`):

| Table | Columns | Notes |
|---|---|---|
| `pjt_concentrics` | `id`, `bundle_id`, `transition_branch_id` (nullable), `notes` | One row = the concentric pack of a bundle, of a transition branch, or -- **[USER, 2026-10-25] when a bundle and a transition branch are connected, of BOTH: they share the one row and the one widget** (`insert(bundle_id, transition_branch_id)`, both typed `bytes \| None`; connecting them = one concentric carries both ids). **Schema bug FIXED 2026-10-25:** `bundle_id` was `no_null=True` while only `transition_branch_id` was nullable, so `_create_branch_concentric`'s `insert(None, branch_db.db_id)` (a branch concentric has no bundle) violated NOT NULL -- the branch path could never have inserted a row. Both columns are now nullable (verified by rendering the DDL with the app's own `SQLTable` and inserting a branch-only and a bundle-only row into a scratch in-memory DB). **Existing project DBs keep the old NOT NULL** (`SQLTable.update_fields` only adds missing columns, it never relaxes a constraint), so they need re-creating. That at least one of the two is set is still enforced nowhere (SQL has no CHECK support here, and `PJTConcentricsTable.insert` does not guard it). Nothing yet MERGES two concentrics when a bundle and a branch get connected -- that step (keep one row, put both ids on it, delete the other and its widget) is open **[OPEN]**. The `bundle_id` FK is correct: `bundle_covers.pjt_table` is the `pjt_bundles` table. |
| `pjt_concentric_layers` | `id`, `concentric_id`, `idx`, `diameter`, `num_wires`, `num_fillers`, `notes` | `diameter` should be the standard's **layer diameter** = envelope diameter of that layer (the circle through the outer sides of its wires) -- see section 5. No lay length / direction columns yet. |
| `pjt_concentric_wires` | `id`, `layer_id`, `wire_id`, `point2d_id`, `idx`, `is_filler`, `notes` | `point2d_id` = the wire's position IN THE CROSS-SECTION (a `pjt_points2d` row). `is_filler` marks filler wires. `Position2DMixin`. |
| `pjt_pegboard_sections` (NEW 2026-10-25, [USER]) | `id`, `concentric_id` (UNIQUE), `point_pegboard_id`, `size`, `is_visible_pegboard` | Position and size of the cross-section widget on the Peg Board. **One row per concentric**; the widget attaches to a bundle or a transition branch through the concentric, and a connected pair shares the one widget. Wrapper `PJTPegboardSection` (`project_db/pjt_pegboard_section.py`), accessor `ptables.pjt_pegboard_sections_table`, `PJTConcentric.pegboard_section`. The row owns its own `pjt_points_pegboard` center point. |

Wrappers: `PJTConcentric`, `PJTConcentricLayer`, `PJTConcentricWire` (`.layers`, `.wires`, `.layer`,
`.concentric`). `PJTBundle.concentric`, `PJTTransitionBranch.concentric`. `pjt_wire_paths` also
carries a `concentric_id` (`PJTWirePathsTable.for_concentric`, `wire_ids_for_concentric`,
`concentric_ids_for_wire/bundle`, `bundle_ids_for_concentric`).

Only creator today: `handlers/transition_handler._create_branch_concentric` -- builds ONE concentric
per transition branch with a SINGLE layer (idx 0) holding every wire, each wire at a dummy
`point2d (0, 0, 0)`, diameter passed in by the caller. **No real layout is computed anywhere.**
Consumers that read the rows: `ui/dialogs/transition_routing.py` (wire labels, effective diameter).

Other consumers of "concentric" as a concept [MEM, circuits section]: `handlers/bundle_diameter.py`
derives the bundle diameter, and the circuit thermal / ambient code derives the BUNDLING TYPE from
the data: concentric if the bundle has `pjt_concentrics` rows, unorganized if wires carry a bundle tag
without one, unpacked if the wire is in no bundle. Whatever this feature writes must keep that rule
true (a computed layout = concentric rows exist).

## 4. The rules (sourced)

### 4.1 Layer structure [STD Table XXI, 600.6.1.28]

- A concentric = a **center** of 1 to 5 touching wires (the center counts as layer 1 "even if only
  one wire"), then layers around it. Each layer after the first has **6 more wires than the one
  under it** (concentric strand: 7, 19, 37, 61 ... for one center wire).
- Equal-size wires. Layer counts and envelope ("layer") diameters, as a multiple of the wire
  diameter d (this is Table XXI exactly; layer 1 = center):

| Layer | 1 in center: wires / total / D | 2 in center | 3 in center | 4 in center | 5 in center |
|---|---|---|---|---|---|
| 1 | 1 / 1 / 1d | 2 / 2 / 2d | 3 / 3 / 2.15d | 4 / 4 / 2.41d | 5 / 5 / 2.7d |
| 2 | 6 / 7 / 3d | 8 / 10 / 4d | 9 / 12 / 4.15d | 10 / 14 / 4.41d | 11 / 16 / 4.7d |
| 3 | 12 / 19 / 5d | 14 / 24 / 6d | 15 / 27 / 6.15d | 16 / 30 / 6.41d | 17 / 33 / 6.7d |
| 4 | 18 / 37 / 7d | 20 / 44 / 8d | 21 / 48 / 8.15d | 22 / 52 / 8.41d | 23 / 56 / 8.7d |
| 5 | 24 / 61 / 9d | 26 / 70 / 10d | 27 / 75 / 10.15d | 28 / 80 / 10.41d | 29 / 85 / 10.7d |
| 6 | 30 / 91 / 11d | 32 / 102 / 12d | 33 / 108 / 12.15d | 34 / 114 / 12.41d | 35 / 120 / 12.7d |
| 7 | 36 / 127 / 13d | 38 / 140 / 14d | 39 / 147 / 14.15d | 40 / 154 / 14.41d | 41 / 161 / 14.7d |
| 8 | 42 / 169 / 15d | 44 / 184 / 16d | 45 / 192 / 16.15d | 46 / 200 / 16.41d | 47 / 206 / 16.7d |
| 9 | 48 / 217 / 17d | | | | |

  Pattern (used to generate rows beyond what is printed): layer n >= 2 holds `6(n-1)` wires for a
  1-wire center, `c + 6(n-1)` for a c-wire center (c = 2..5); every layer adds `2d` to the envelope;
  the center-layer factor is `1 + 1/sin(pi/c)` for c >= 2 (2, 2.1547, 2.4142, 2.7013 -- the table
  rounds to 2.15, 2.41, 2.7) and 1 for c = 1. [DERIVED, matches every printed row]
- `D = f d` for the cable diameter of an equal-wire cable ("cable factor", 600.6.1.18).
- [HPA] agrees: core of no more than five cables; each layer one conductor size; layer wire count
  from a lookup table of (previous layer diameter / this wire's diameter).

### 4.2 Hybrid (mixed-size) calculation, step by step [STD 600.3.9, Figure 5, worked example]

1. **Core diameter** = core wire diameter x Table XXI factor for the number of wires in the center.
2. **Next layer's wire count N** = capacity of a ring of the next wire size on that envelope:
   divide the previous layer diameter `D` by the new wire's diameter `d` and read N from Figure 5.
3. **New layer diameter** = previous layer diameter + 2 d.
4. Repeat. If wires of that size are left over after a layer is full, a further layer is added;
   the standard's text then completes that layer with fillers of the same diameter.
5. **Always use maximum diameters / thicknesses** -- that gives the worst-case (form, fit, function)
   cable diameter.

Figure 5 caveats: valid only for N >= 10 (below that use Table XXI); the formula is in section 5.1.

### 4.3 Lay length [STD 600.3.5, Figure 4; TE; HPA]

- "Cable lay length" = axial distance advanced by one full turn of any one component in the layer.
- **Good cable design: lay length = 8 to 12 times the LAYER diameter; 10x is the usual default**
  (best economy and flexibility). Twisted pairs / triads are laid at 8 to 16x and are "not to be
  confused with cable design". [STD] [HPA: 8-12x] [TE: "usually between 8 and 16 times"]
- Each layer has its own lay length (proportional to its own layer diameter -- Figure 4: 3.9"
  / .387" = 10.08x, 6.2" / .617" = 10.05x, 7.3" / .733" = 9.96x; the CORE is laid at 10x as well).
  [HPA: core lay "found by feel", usually longer -- a practice note, not the standard.]
- Longer lay = stiffer cable; shorter lay = more flexible. **Lay length may be DECREASED to complete a
  layer that would otherwise need a filler.** [STD]
- A layer's "layer diameter" is its envelope diameter D_n (the standard's DIA. column), not the
  wire-center circle.

### 4.4 Lay direction [STD 600.3.8, 600.6.1.25 / .28 / .33 / .57; TE; HPA]

- Two allowed styles: **contrahelical** (each layer opposite to the one beneath) or
  **unidirectional** (all one direction; "pitch varied" -- the lay length must then INCREASE with each
  successive layer). [STD 600.6.1.25] TE and HPA only describe the alternating style.
- **Standard direction of the OUTER layer is LEFT hand.** [STD] "Always aim to have the outer layer
  as a left hand lay." [TE] Best practice, not always feasible (HPA used a right-hand outer layer
  under a shielded outer).
- Direction of lay = the lateral direction the elements run over the TOP of the cable as they recede
  from an observer looking along the axis. Left hand = passes to the left. [STD 600.6.1.57, TE]
  Figure 4 example: core L/H, layer 1 R/H, layer 2 L/H, wrap L/H.
- Binder / lacing is laid OPPOSITE to the outer layer. [TE, HPA]
- Shielded cables / twisted pairs: lay them opposite to their own internal twist so they stay pairs
  and do not become a "quad". [TE, HPA]
- Branches: lay each branch from the center sections / transitions out to the ends and keep the
  OUTER-layer lay direction the SAME for every branch. [TE]

### 4.5 Placement of elements [STD 600.3.4, 600.3.8]

- Mixed sizes / complexes (shielded pairs, coax): place the **larger elements in or near the
  core** (they carry more tensile load because of the shorter lay in the core); smaller conductors in
  the outer layers. Where impractical, large conductors may go on the periphery and small ones may be
  "roped" to get uniformity and flexibility. [STD, HPA: core = the largest conductors]
- **CONFLICT:** [TE] says the opposite for hybrids: "place the larger diameter wires in the outer
  layers"; failing that, group small wires to approximate the large ones, or lose leftover small wires
  in the interstices. See section 6.
- **Coax should not be in the center.** A **single wire (shielded or not) should not be the center**
  where avoidable: it is a straight line, has no lay length and cannot take up length when flexed.
- Fillers may replace a conductor in any layer; **economically best in the outer layer**.
- Twisted pairs nest into each other -- core diameter reduction "normally 12 percent". [STD]
- Goal: a flexible, **circular cross-section with the smallest overall diameter**. [STD, TE: "fillers
  as required to maintain a circular cross section"]
- Batch building / ease: group wires that branch off together next to each other; ideally wires
  leaving at a branch come from the OUTER layers (a core wire needs the twist unwound back to the
  core). [HPA]

### 4.6 Fillers [STD 600.3.10, Table XXII]

Filler diameter = F x d, where d is the diameter of the flanking wires and N is the number of wires
in the lay (ring) the filler sits around (filler nests in the outer valley between two ring wires):

| N wires in the layer | 2 | 3 | 4 | 5 | 6 | 7 | 8-10 | 11-17 | 18-24 | 25 and up |
|---|---|---|---|---|---|---|---|---|---|---|
| F | .67d | .50d | .41d | .39d | .37d | .34d | .32d | .31d | .28d | .25d |

Fillers must keep their position and not shrink ("pack") in service; materials: cotton, jute, vinyl,
polyethylene, fiberglass, twisted polyethylene monofilament. They also cushion flexing / impact.

### 4.7 Build-up outside the lay pattern [STD 600.3.7, Figure 4]

- Binder / separator tape: helical, overlap from 75 percent to open (50 percent most common). Figure 4
  adds a Mylar wrap `.022 x 1.0, 50% overlap` as `.002 x 4 = .008` of diameter; the braid shield
  adds `.028` (85 percent coverage, #34); the jacket adds `2 x wall` (`2 x .0625 = .125`).
  Outer diameter = layer diameter + those. (Later layers of the model, not part of the packing.)

### 4.8 Length / cut allowance [TE, HPA]

- "Cut wires to length + 20% for Lay Loss and end tapes." [TE] [HPA: add roughly 25-30% to outer
  layers] -- both are shop allowances. The pure geometric growth is 3-7% (section 5.4); the rest is
  trim / termination allowance.

### 4.9 Inspection / visual [TE]

No crossovers, no flip-overs, even lay, correct wire count and types per layer, every layer (and the
binder / wrap) in the opposite direction, no scraped / nicked wires; lay too short = over-twisted,
too long = under-twisted. Hand laying suits cables up to about 12 m.

## 5. Layer-packing math

Notation: wire diameter d, envelope ("layer") diameter D_n of layer n (after adding that layer),
wire-center circle radius R_n, lay length L_n, lay ratio lam_n = L_n / D_n, lay angle alpha_n.

### 5.1 Layer capacity -- the standard's Figure 5 formula [STD, verified]

```
              pi
N = ------------------------------        x = D / d   (D = previous layer's envelope diameter,
     asin( (1 + eps) / (x + 1 + eps) )          d = diameter of the wire being laid)

eps = Z/d = 0.047 in the standard ("4.7% is the increase in the wire dia. when each layer
increases 6 wires on account of the angle of the lay")
```

Verification run against Table XXI (this session's script, N >= 10 entries, 33 of them): reading
`(1+eps)/(x+1+eps)` with eps = .047 reproduces **27 / 33** exactly with `floor`; the 6 misses are all
in the "2 in center" family, where the table counts follow the structural `c + 6(n-1)` rule and the
formula allows one wire more. The alternatives fail badly: `(1+eps)/(x+1)` 25 / 33, and no lay
correction at all (eps = 0) only 6 / 33. Worked example: formula gives 13.1, 35.0, 41.0 where the
standard's text reads 13, 34, 41 from the chart -- the hand-read chart is within one wire.
So: **standard lay = the structural counts of Table XXI; hybrid = this formula, plus a conservative
-1 allowance [OPEN: decide].** (The scale in Figure 5 and the formula's last symbol are smudged in the
PDF; the reading above is the one that reproduces the tables.)

### 5.2 Where the 4.7% comes from -- capacity depends on the lay ratio [DERIVED]

A helical wire cut square to the bundle axis is an ellipse, tangentially wider by `1 / cos(alpha)`.
With the lay angle from `tan(alpha) = pi * D_c / L` and the lay ratio `lam = L / D_c`:

```
eps(lam) = sqrt(1 + (pi / lam)^2) - 1
lam =  8x: 7.43 %   (alpha 21.4 deg)
lam = 10x: 4.82 %   (alpha 17.4 deg)   <- the standard's constant (4.7 %) is the 10x lay
lam = 12x: 3.37 %   (alpha 14.7 deg)
lam = 16x: 1.91 %
```

Consistent with Figure 4 (all layers laid at ~10x). So `N(x, lam)` = Figure 5 with `eps(lam)`:
a shorter lay makes each wire's section wider and the layer holds FEWER wires, which is exactly the
standard's "decrease the lay length to complete a layer that would need a filler" (e.g. x = 10.64:
8x holds 34.2, 10x 35.0, 12x 35.4, 16x 35.9). The lay ratio is therefore a real per-layer input to
the solver, not just a display value.

### 5.3 Envelope, wire positions, cross-section geometry [STD + DERIVED]

- Envelope progression: `D_n = D_(n-1) + 2 d_n` (the standard's step; ignores nesting, so it is
  slightly conservative / worst case). Core: `D_1 = d * (1 + 1/sin(pi/c))` (c >= 2), `d` for c = 1.
- Wire centers of layer n sit on a circle of radius `R_n = (D_n - d_n) / 2`, N_n wires evenly spaced
  at angle `2 pi / N_n` (rotate by half a step per layer so wires nest in the valleys of the layer
  beneath -- for display; the standard does not prescribe it).
- Core with c touching wires: centers on a circle of radius `d / (2 sin(pi/c))` (c = 2: `d/2`;
  c = 1: at the origin). Valley wires of the core (Figure 4's three #20 SC in the three outer valleys
  of the three TPSJ) use Table XXII with N = c.
- Mixed sizes within one ring (not covered by the standard): ring-fit equation
  `sum_i 2 asin((r_i + r_(i+1)) / (2 R)) = 2 pi` solved for R by bisection -- the seed for the
  relaxation pass. [GK]

### 5.4 Wire length growth [DERIVED]

Length of a wire per unit bundle length = `1 / cos(alpha) = sqrt(1 + (pi D_c / L)^2)` = `1 + eps`.
Because L is proportional to each layer's own diameter, the angle (about 15-17 degrees) and thus the
growth (about 3-5 percent at 10-12x lay) is nearly the SAME for every layer -- outer wires are not
much longer than inner ones. Cut length = bundle path length x (1 + eps) + the shop allowances of
section 4.8.

### 5.5 Fillers -- closed form of Table XXII [DERIVED, cross-checked]

Filler in the outer valley between two touching ring wires, not protruding past the ring's outer
envelope circle, tangent to both flankers:

```
f / d = (1 + t)^2 / ( 2 (2 + t) ),     t = tan( pi / (2 N) )
N = 2: .667   3: .483   4: .414   5: .378   6: .354   7: .339   10: .311   18: .283   large N: .25
```

Equals Table XXII at N = 2, 4, 7 and 18, within ~.02d elsewhere; the table is rounded and, for
N >= 25, lower (.25d vs the true .27d). The N -> infinity limit `d/4` is the "filler = flank / 4"
fact in [MEM]. **Use Table XXII as the rule (it is the standard); the closed form is for the
relaxation solver and as a cross-check.**

### 5.6 Capacity bounds for sanity checks [GK]

Equal-diameter ring on center circle radius R: `N_max = floor(pi / asin(d / 2R))`; for the hexagonal
nest `R = k d` this gives 6, 12, 18, **25**, 31 for k = 1..5 -- at k = 4 geometry allows 25 but the
standard's count is 24 (the +6-per-layer rule wins; the spare is looseness). The lay correction
`eps` explains the difference.

## 6. Source conflicts and gaps (decide with the user)

1. **Where do big wires go?** [STD] / [HPA]: larger elements in the core, small outside. [TE]: larger
   wires in the OUTER layers. Plan: implement a placement policy setting with `STD` (default) and
   `TE`, and always flag when a layout violates the selected policy. [OPEN]
2. **Lay ratio range:** [STD] 8-12x (10x typical); [TE] "usually 8-16x". Plan: default 10x, allowed
   8-12x, warn (not error) up to 16x. [OPEN]
3. **Unidirectional lay** (lay length increasing per layer) is allowed by [STD] but never described
   by [TE] / [HPA]. Plan: v1 alternating only; keep a `lay_direction` per layer in the schema so
   unidirectional can be added. [OPEN]
4. **One wire size per layer** ([HPA], implied by the standard's method). Mixed sizes in a layer are
   not covered; plan: refuse in v1, flag as a rule violation, optionally relax via the ring-fit
   equation (5.3) later. [OPEN]
5. **Core lay:** [HPA] "by feel, longer"; [STD] 10x like the others. Plan: follow [STD]. [OPEN]
6. The standard's example text and its own figure disagree on the 3 leftover #20 wires: the TEXT puts
   them into an extra layer with 38 same-size fillers; FIGURE 4 puts them into the core's valleys
   (3/20 SC beside 3/20 TPSJ) where Table XXII (F = .50d = .090" for d = .180") says they fit.
   Plan: valley placement first (it is far smaller), extra layer only if valleys cannot take them.
7. MIL-STD-339 is cancelled; MIL-HDBK-508 is guidance only. The rules here are therefore industry
   practice with a published origin, not a current contractual requirement.

## 7. Acceptance test: the standard's worked example (Figure 4, 600.3.9)

Input (all wire per MIL-W-16878/4, max diameters): 3 x 20 TPSJ (.180), 13 x 16 SSJ (.115),
37 x 20 SC (.058). Expected output:

| Layer | Content | Calc | Layer dia | Lay length | Dir |
|---|---|---|---|---|---|
| Core | 3 x 20 TPSJ + 3 x 20 SC (valleys) | .180 x 2.15 | .387 | 3.9" | L/H |
| 1 | 13 x 16 SSJ | .387 / .115 = 3.4 -> N = 13; + 2 x .115 | .617 | 6.2" | R/H |
| 2 | 34 x 20 SC (37 - 3 in the core valleys) | .617 / .058 = 10.6 -> N = 34; + 2 x .058 | .733 | 7.3" | L/H |
| Wrap | Mylar .022, 50% overlap | .002 x 4 = .008 | .741 | -- | L/H |
| Shield | #34 braid, 85% | +.028 | .769 | -- | -- |
| Jacket | 3/4 x 1/16 wall | 2 x .0625 = .125 | **.894 max** | -- | -- |

The solver must reproduce this table (counts, diameters, directions, lay lengths within rounding)
before anything else is built on it. Known wrinkle: formula 5.1 gives 35.0 for layer 2, the standard
read 34 from its chart -- decide the rounding rule so this example comes out as printed.

## 8. Solver architecture (proposed -- revised after the research)

The 2026-07-14 baseline [MEM] said the solver is not closed form and needs a relaxation pass. That
still holds for the FINAL geometry (valley wires, fillers, mixed sizes), but the research shows the
LAYER STRUCTURE is a deterministic, closed-form procedure (section 4.2 / 5.1) -- so:

**Stage A -- lay-pattern calculator (deterministic, headless, instant).** Rules as data + the 4.2
procedure: choose the center, assign wires to layers under the placement policy, compute N per
layer (5.1 / 5.2), fillers / valley placement (4.6), envelope diameters, lay lengths and directions
(4.3 / 4.4), warnings. This is the seed AND, for single-size wires, the whole answer.

**Stage B -- geometric positions + relaxation (only where needed).** Angles and radii from 5.3 for
the cross-section view; a physics-style relaxation (overlapping circles repel, settle toward
`R_n`) only for hybrid layers / valley wires / fillers where the closed form is not exact. Keep the
speed target [MEM]: well under a second for hundreds of wires (the old Copilot packer took ~10 min
for ~75 wires because it was unconstrained annealing with no deterministic seed -- do not repeat).

New modules (pure Python + numpy first; Cython only if measured; **no GUI imports** so it can run
headless): `concentric_rules` (the tables above as data, each row citing its source),
`concentric_pack` (input: wire id, outer diameter, kind = single / twisted pair / shielded /
coax / filler; output: `ConcentricLayout` = center + layers, each with ordered wires, angular
positions, R_n, D_n, N_n, lay length / ratio / direction, fillers, warnings, outer diameter).

Persistence: write into `pjt_concentrics` / `_layers` / `_wires` -- `point2d_id` = (x, y) in mm from
the bundle axis, `idx` = order in layer, layer `diameter` = D_n. NEW columns needed on
`pjt_concentric_layers`: `lay_length`, `lay_direction`, probably `lay_ratio`; on `pjt_concentrics`:
`placement_policy`. The project DB is pre-release: no migration shims (MEMORY.md "No backwards
compat pre-release"). Recompute when a wire is added / removed / re-sized in the bundle and at every
composition-change point along the run (section 9).

Two cross-section behaviors, not one solver [MEM]: the **concentric pack** (trunk) and the
**transition bulb** at true branches (real harnesses deliberately do not hold the concentric pack
through a branch -- the bundle bulbs where wires leave, doubling as strain relief). Mid-run
composition changes without a branch (pin-splitting a load across two wires) still need the
repack-vs-filler-vs-shorter-lay decision, and 5.2 now gives the "shorter lay" option real numbers.
Claude, if embedded, is only the orchestration / judgment layer for those tradeoffs, never the
geometry compute [MEM].

## 9. Display (cross-section view)

### 9.0 The widget -- user spec, 2026-10-25 (written down verbatim in substance)

**Architecture [USER]:** a custom-drawn widget that looks like the cross-section of the harness. It is
built the same way as the pegboard view tables (`ui/pegboard_table/mdi_host.py` ->
`objects/objects_pegboard/table.py`): create the widget, have it write to a buffer, and use the buffer as
a texture in OpenGL in the pegboard view. Details matter: every wire is rendered correctly.

**Rendering rules [USER]:**

1. **Single-conductor, unshielded wire.** Outer circle = the wire's `od_mm` (total outside diameter
   INCLUDING insulation). Next, the conductor circle, diameter from the wire size (`conductor_dia_mm`),
   filled with a SOLID color that is a close match to the conductor material (copper, tin, silver, ...).
   The space between the conductor diameter and the OD is filled with a solid color matching the wire's
   primary color. If the wire has a stripe, pick a (random) location and draw what the cross-section of
   the stripe would look like, in the stripe color.
2. **Multi-conductor wire with no shield and no outer jacket** (typically a twisted wire). Show each
   conductor, packed together as tightly as possible while staying as close to a circle as possible
   around all of them. Each conductor is rendered exactly like a single-conductor wire (rule 1).
   **Repositioning moves the whole cable as ONE unit** -- all conductors move together.
3. **Multi-conductor wire with an outer jacket and optional shielding.** Render the jacket and the
   shielding along with the individual conductors.
4. **Coax.** Render the conductor, inner insulation (dielectric), shielding and outer insulation
   (jacket).

**Layout and information pane [USER, 2026-10-25]:** the widget is split into TWO sections side by side.
The right one has a **sash that can be dragged to close and open** the extra information, just like the
circuit editor. It fills in for the wire selected on the left with: color, size, part number, the wire's
**calculated length using helix math (the formula the wire service loop uses)**, the **current through
the wire** (available from the circuit solver) and the **approximate maximum wire temperature** during
operation.

**Position and size [USER, 2026-10-25]:** an additional database table, `pjt_pegboard_sections` (section
3): ONE row per concentric widget, holding the widget's position and size and the concentric's row id. A
widget attaches to a bundle OR a transition; when a bundle and a transition branch are connected, ONE
widget exists for both (they share the one concentric).

**Built (2026-10-25):**

- `ui/concentric_section/` (see its `MAP.md`): `section_model.py` (plain-data conductor / shield / jacket /
  cable / section / `WireDetail` specs, `helix_length_mm`, `conductor_rgb`, `stripe_angle_for`),
  `packing.py` (circle-in-circle packing for rules 2-3), `wire_painter.py` (rules 1-4), `section_view.py`
  (the custom-drawn left pane: select a cable, drag it and ALL its conductors together),
  `info_panel.py` (the right pane), `section_widget.py` (`ConcentricSectionWidget`: both panes in a
  `QSplitter`, `host_offscreen()`, `resize_mm()` and `grab_rgba()` -> the same `(bytes, width, height)`
  RGBA8888 buffer contract as `PegboardTableHost.grab_rgba`).
- The `pjt_pegboard_sections` table: schema `create_database/pegboard_sections.py`, wrapper
  `project_db/pjt_pegboard_section.py`, registered in `pjt_bases.py` and in `PJTPointPegboard.is_referenced`,
  with `PJTConcentric.pegboard_section` and a `PJTConcentric.delete()` that removes the widget row first.

- **The pegboard GL object (2026-10-25)**, modelled on `objects_pegboard/table.py`: `ui/concentric_section/
  section_host.py` (`ConcentricSectionHost`: the widget in a hidden `QMdiArea` / `QMdiSubWindow` for a real
  title bar, close, move and resize, plus the synthetic mouse / wheel dispatch), `objects/objects_pegboard/
  section.py` (`Section`: texture upload through `TextureProgram`, the quad at the row's position and size,
  selection ring, resize through the ring, interaction forwarded only while selected), the facade
  `objects/pegboard_section.py` with inert 3D / schematic placeholders, `PJTPegboardSection.get_object` /
  `set_object`, `ObjectBase.is_pegboard_section`, `gl/object_picker._render_id_of` ranking a section against
  the wire tables (one shared render counter), and `Project.__init__` restoring every existing row.
  A concentric deleted with its widget now frees the widget's GL textures and hidden host
  (`PJTConcentric.delete()` goes through the live facade). The wire table's own object leaks its textures;
  that was left alone.

**Checked (GL object, 2026-10-25; scratch scripts, sandboxed, `GL` mocked and the heavy app modules stubbed --
NOT in the real app):** the texture is uploaded at the widget's size and the row's size / scale follow it;
canvas pixels map to the widget exactly (a click on a cable selects it, a drag moves it by the expected
distance); an unselected section consumes nothing; hover is consumed inside and not outside; the green ring is
a resize handle with the right cursor, the clamp holds, and the real sub-window follows; the wheel scrolls the
information pane and is NOT consumed elsewhere; a title-bar drag moves the section in the world and fires the
position callbacks once; the close button hides it; `render()` uses `shaders.texture` and the shared counter;
the title names the bundle and / or transition; `_delete` frees both textures. **Not checked:** anything that
needs a real GL context (the shader, the ring, the depth ordering, the texture's appearance), the picker, the
canvas's own event routing, and `Project.__init__` loading a real row.

**Drag a wire from the wire table onto the concentric widget [USER, 2026-10-25] -- built.** Press a wire row in
a peg-board wire table, move the pointer, and drop it on a concentric section widget: the wire is added to that
concentric. How:

- Both panels are GL textures, so Qt's own drag and drop cannot carry it. `objects_pegboard/table.py`'s
  `Table` turns a press on a wire row that moves 6 px into a drag of that wire (`_wire_at` reads the row, the
  press is ended as the click it would have been); `objects_pegboard/wire_drop.py` finds the drop target
  under the pointer; `Section` is that target (an ORANGE ring while a wire is over it, a copy cursor, a
  forbidden cursor elsewhere). On release `Section.accept_wire_drop` calls `handlers/concentric_handler.
  add_wire`, then `reload()`.
- `handlers/concentric_handler.py` (new): `add_wire` (a `pjt_concentric_wires` row in the outermost layer;
  layer 0 is made if there is none; a duplicate is refused), `replan`, `needs_plan`, and `build_section`
  (the database -> `SectionSpec` + `WireDetail` adapter, with the current and temperature from
  `circuit.solve()`). `Section.__init__` now calls `reload()`, so a restored section shows what its
  concentric already holds.
- **Layer diameters are not touched.** `bundle_diameter._wires_diameter` uses the OUTERMOST layer's `diameter`
  as the bundle's size as soon as its concentric has any layer, so a new first layer is given the diameter
  the bundle has right now and an existing layer's is never rewritten; otherwise a drop would silently resize
  the bundle in 3D and on the peg board.
- **INTERIM, until the layer solver exists:** `replan` packs every cable as tightly as it can in a circle (not
  the MIL-STD-339 layer plan) and overwrites every cable's place on each add; a manual drag of a cable is
  still not saved. A coaxial or shielded part is drawn with a shield and a jacket (4 % and 10 % of its OD, not
  in the data), anything else without (several conductors = a twisted group) -- the missing jacket flag
  (above) is still open.
- **Checked (scratch scripts, no real app or database):** the handler against fake rows (no duplicates, layer
  diameters untouched, no overlapping cables, the four cable kinds, the details incl. solver numbers); the
  `Table` drag against a real `QTableView` (header never starts one, a click is still a click, the topmost of
  overlapping targets wins, release hands over the right wire id, cancel / deselect / delete clean up); the
  `Section` target (contains / hover ring colour / accept / duplicate / reload plans first).
  **Not checked:** the shader drawing of the orange ring, the cursors on a real canvas, the canvas's own
  routing of the release to the table, anything against the real `PJT*` rows, and the drag with two real
  panels on screen.
- **Open:** nothing checks that the dropped wire actually runs through the bundle (or transition branch) the
  concentric belongs to -- any wire in any wire table can be dropped on any section. **[OPEN]**

**A Qt finding worth keeping:** after a programmatic `QMdiSubWindow.resize()` the title bar's close button
stopped answering clicks (it stayed drawn in its hover colour) until the sub-window was deactivated and
re-activated; a hover, a repaint, `processEvents` and `hide()` / `show()` did not help. `ConcentricSectionHost.
resize_sub_window()` does the re-activation. It was found in a scratch script, so whether the app (and the wire
table, which resizes the same way) needs it is unconfirmed.

**Checked (scratch scripts in a sandboxed app-data folder, Qt on the real platform with the widget
`WA_DontShowOnScreen`, never the real app):** one cable of each kind drawn (single wire with a stripe, twisted
pair / triple / 10-group with no jacket, 4-conductor shielded jacketed, 7-conductor jacketed, coax) with
no overlaps; the buffer comes out RGBA 720 x 360 for the 120 x 60 mm default (alpha 0 where nothing is
drawn); the sash closes and reopens from code AND by dragging the real handle with the mouse; dragging a cable
moves it by exactly the mouse distance, as one unit (its conductors' relative places are untouched) with the
panel's helix length following; clicking empty space clears the selection; the table's UNIQUE
`concentric_id` rejects a second widget for the same concentric. **NOT verified:** the type hints (the
runtime recorder is switched off since commit c80bd9f; the new code was reviewed by hand against the repo's
hint rules only), nothing was run in the real app, and nothing here has been compiled with Cython.

**"Show Concentric Section" on the bundle and transition-branch context menus [USER, 2026-10-25] -- built.**
The action creates the `pjt_pegboard_sections` row (or re-shows one the user closed) and builds the
`PegboardSection` facade, so a wire can then be dropped on it. How:

- `BundleMenu` gets one action; `TransitionMenu` gets one per BRANCH (the concentric belongs to a branch, not
  to the transition): a plain action for a single branch, a submenu `Branch <branch_id>` for several, none for
  a transition with no branch. Each is disabled while its widget is showing; after the user closes the
  widget (title-bar button, which sets `is_visible_pegboard` false) it is enabled again and just un-hides it.
- Which concentric (`handlers/concentric_handler.find_concentric_for_bundle` / `_for_branch`, read-only, and
  `concentric_for_bundle` / `_for_branch`, which make an empty one when there is none, only when the action
  is used -- opening the menu changes nothing): a bundle uses its own, else the first among the branches
  plugged into either end; a branch uses its own, else its bundle's. That is how a connected bundle and
  branch share ONE widget -- by lookup, no id is rewritten. If BOTH already had a concentric before they were
  joined each keeps its own (two widgets); nothing merges them (open item 3 below).
- Placement (`objects/pegboard_section.PegboardSection.show`): `table_placement.find_free_position` from the
  bundle's midpoint, or the transition's position, avoiding the footprints of the visible objects. It returns
  the CENTRE of a free rectangle and the widget is drawn from its LEFT edge, so the stored X is the centre
  minus half the width. The existing wire tables store the centre directly (`BasePegboard.show_table`), so
  they land half a width to the right of the spot found -- a latent offset in existing code, left alone.
  **[OPEN]**
- **Checked (scratch scripts, fakes only, real `BundleMenu` / `TransitionMenu` classes on offscreen Qt):** the
  lookups (fresh / own / shared in both directions / conflict keeps its own / created once / read-only find),
  the menus (no, one and three branches, sorted, the right branch bound to each entry, disabled while
  showing, the midpoint anchor), `show` (new row at the left-edge position and default size, moved clear of an
  obstacle, closed row un-hidden in place, live facade reused), and the two `BasePegboard` helpers. The
  modules import in the app's own order (`ui` first). **Not checked:** the menus in the real app (right-click
  on a real peg-board bundle / transition), the real `PJT*` rows, and the widget actually appearing on
  screen.

**Not built / open [OPEN]:**

1. ~~Nothing creates a `pjt_pegboard_sections` row~~ -- now done (the item above). Still open: a widget
   closed with its title-bar button has no other way back than the same menu action, and the transition
   menu lists the branches only (nothing offers a concentric for the transition as a whole, because there is
   none). **[OPEN]**
2. The adapter from the database to a `SectionSpec` / `WireDetail`: sizes and colours from the wire part,
   the current and temperature from `circuit.solve()` (`CircuitSolution.amps[wire]` /
   `.temperature[wire]` / `.over_temp` / `.runaway`), the layout from the concentric layer solver (not
   written yet, sections 5-8). There is **no jacket flag on the `wires` table** (it has `num_conductors`,
   `shielded`, `tpi`, `wire_type`, `od_mm`, `conductor_dia_mm`, `core_material`, `color`, `stripe_color`),
   so "multi-conductor, unshielded" cannot be told apart as twisted vs jacketed from data alone.
3. Merging two concentrics (and their two widgets) when a bundle and a transition branch get connected.
4. Packing for 8-19 equal conductors is within 0-6.5% of the best known enclosing circle (exact at 8, 9
   and 13); the best-known values were quoted from memory.

**Lessons (Qt):** a `QSplitter` does not pass height-for-width to its panes, so wrapped labels were clipped
to one line until the pane's content went inside a `QScrollArea`; Qt's `offscreen` platform on this machine
has no fonts (every glyph is a box), so render on the normal platform with `WA_DontShowOnScreen`; the
scratch-script sandbox (`APPDATA`, `USERPROFILE`, `HOME` pointed at a scratch folder) is needed even with a
stubbed top-level package, because `config` creates its app-data folder when imported.

### 9.1 Requirements

- **Hard requirement [MEM]: a cross-section must be renderable at EVERY location where bundle
  composition changes** (every branch / pin-out point), not once per run.
- Content: envelope circle per layer (the layer diameters), every wire a circle at true outer
  diameter colored by its color code / circuit, fillers distinct, valley wires in the core visible,
  layer rings as faint guides, lay direction (L / R) and lay length per layer, wire labels on
  hover, readout of N per layer / total / outer diameter / filler count, plus the warning list
  (policy violation, lay ratio out of 8-12, circular-section deviation, over-capacity layer).
- Also useful: a **side view** showing the spiral, lay length and direction (lower priority).
- Where it appears **[OPEN]**: a dockable panel driven by the current selection, and / or inside the
  bundle's floating table in the peg-board editor, and / or a 3D overlay. A plain QPainter widget is
  probably enough (tens to hundreds of circles, no GL pipeline needed) -- check against the canvas
  rules in MEMORY.md (`new_canvas2d`) first.
- The existing `pjt_concentric_wires.point2d_id` rows are exactly what the view reads.

## 10. Implementation plan (phases)

1. **Research finish:** read MIL-HDBK-508 (successor) for changes to Table XXI / lay rules; read
   TE ELE-3COP-257 / 258 (binder / wrap); optional cross-checks (IPC/WHMA-A-620 twisted-wire lay,
   NASA-STD-8739.4, ASTM B8 concentric-lay conductors) -- none of these block Phase 2.
2. **Rules module + lay-pattern calculator (Stage A)**, headless. Acceptance = section 7's table.
   Validate with a diagnostic script that also dumps Table XXI vs the structural / formula counts
   (the one used in the research, `check_table21.py`, is the template).
3. **Positions + filler / valley placement + relaxation (Stage B)** and the `ConcentricLayout`
   object.
4. **Persistence** (schema additions, write the layout for a bundle / branch; keep the derived
   "bundling type" rule of section 3 true; make `PJTConcentricsTable.insert` enforce exactly one of
   bundle / transition branch -- the NOT NULL schema bug of section 3 is already fixed).
5. **Cross-section view** for one concentric (read-only), then at every composition-change point.
6. **Transition bulb** model and the branch-point behavior (TE: same outer-layer direction on all
   branches; wires leaving at a branch come from the outer layers).
7. **Interaction:** user overrides (pin a wire to a layer / swap positions / lay ratio per layer /
   placement policy), re-pack.
8. **Feed-forward** to the rest of the app: bundle diameter (`handlers/bundle_diameter.py` -- today
   count-based; replace with D_n + build-up), wire cut length (5.4), and the circuit thermal /
   ambient calculation (real layer positions instead of only counts).

Do NOT write unit tests (project rule, MEMORY.md); validate with diagnostic scripts.

## 11. Research log

2026-10-25 (all via WebSearch / WebFetch):

- First three searches (lay-length rules for MIL-W-22759 / MIL-C-27500; concentric stranding 6-12-18;
  MIL-DTL-27500 lay) were thin: MIL-DTL-27500 is the shielded / jacketed CABLE spec, not the harness
  twisting standard. The WIA glossary page for "true concentric" now redirects to a product page, so
  the snippet claim "layer direction reversed, lay length growing each layer" is unverified there;
  [STD] 600.6.1.25 / .28 / .33 gives the verified definitions.
- The HPA course page named the standard (MIL-STD-339 Section 600) and the TE document
  (ELE-3COP-256); EverySpec gave the PDF; PyMuPDF / pdftotext extracted text; Table XXI, Figures 4-5
  and Table XXII were read from page images (the OCR text of the tables is garbled).
- The fetch tool saved copies of the two PDFs to `C:\Users\drsch\.claude\projects\...\tool-results\`
  automatically (not requested; contents were only read / text-extracted, never executed).

Still to find, in priority order:

1. MIL-HDBK-508 text (everyspec link in section 2).
2. TE ELE-3COP-257 (binder) and -258 (wrap) -- wrap / binder build-up numbers for the envelope.
3. IPC/WHMA-A-620 (twisted-wire / lay requirements), SAE AS50881, NASA-STD-8739.4 workmanship -- only
   as cross-checks of the 8-12x / 8-16x lay range and handedness.
4. Cable-industry stranding references (ASTM B8 concentric-lay conductors) for another look at the
   per-layer lay range -- optional.

## 12. Open questions for the user

1. Display: dockable panel, part of the bundle table, or a 3D overlay? (section 9)
2. Placement policy default: MIL (larger wires in the core) with TE as an option -- OK? (section 6.1)
3. Lay ratio: default 10x per layer, editable per bundle, allowed 8-12x -- OK? (section 6.2)
4. Twisted pairs, shielded wires, coax and multi-conductor cables inside a bundle: counted as one
   round element of their overall diameter in v1? Does the wire data have a "type / complex" notion
   (TPSJ, coax) or only a diameter? (affects the "no single wire in the core / coax not in the
   center" rules)
5. Recompute the layout automatically on every composition change, or only on a user "Re-pack"?
6. Rounding rule for capacity (section 5.1 / 7): `floor(N)`, or `floor(N) - 1` to match the
   standard's hand-read chart?
7. DB: add the new columns now (pre-release, so yes by the no-backcompat rule)?

## 13. Decision log

- 2026-10-25: Design doc created as `CONCENTRIC_TWIST_DESIGN.md`; the 2026-07-14 requirements in
  MEMORY.md are the baseline.
- 2026-10-25: Governing source confirmed as MIL-STD-339(AT) Section 600 (title corrected, it is a
  combat-vehicle wiring standard, cancelled -> MIL-HDBK-508), with TE ELE-3COP-256 as the second
  primary source. The layer structure is a closed-form procedure; relaxation is only for final
  geometry. No implementation decisions made yet.
- 2026-10-25: [USER] widget spec (section 9.0): custom-drawn cross-section, rendered to a buffer and used
  as a texture in the Peg Board like the wire tables; split into two side-by-side panes with a draggable
  sash like the circuit editor; the right pane shows the selected wire's color, size, part number,
  helix-calculated length, current and approximate maximum temperature. A cable (all conductors) moves as
  one unit.
- 2026-10-25: [USER] "drag and drop a wire from the wire table in the pegboard view over to the concentric
  view to have it add a wire into the concentric planning." Built (section 9.0). My choices: a wire is "in" a
  concentric through a `pjt_concentric_wires` row (not the `pjt_wire_paths` tag, which nothing reads); it goes
  in the outermost layer; layer diameters are never rewritten (the bundle diameter rule reads them); the
  layout is the interim circle pack until the MIL-STD-339 solver replaces `replan`; the drag is built on the
  canvas (not Qt drag and drop) with the target found through `wire_drop`; no check that the wire runs through
  the bundle.
- 2026-10-25: [USER] asked for the pegboard GL object (upload `grab_rgba` through `TextureProgram`, quad at
  the row's position and size, forward mouse events, modelled on `table.py`) and `get_object` / `set_object`
  on `PJTPegboardSection`. Built (section 9.0). My choices: a hidden `QMdiSubWindow` host so the panel gets a
  real title bar / close / move / resize like the wire tables; the dispatch lives in the host so it is
  testable without GL; the wheel is consumed only over the information pane; the quad is anchored like the
  table's (position = LEFT edge in X, vertical middle in Z), which also corrects my earlier "center" wording
  for `pjt_pegboard_sections.point_pegboard_id`.
- 2026-10-25: [USER] "add a 'Show Concentric Section' action to the bundle and transition-branch context
  menus ... create the pjt_pegboard_sections row (or re-show a closed one) at a free spot using
  table_placement.find_free_position, and build the PegboardSection facade, so I can drop wires". Built
  (section 9.0). My choices: the transition menu is per branch (a concentric belongs to a branch), a single
  branch gets a plain action and several a submenu named by `branch_id`; the concentric is made only when the
  action is used; sharing between a bundle and its branch is a lookup (no ids written) and the conflict case
  keeps two widgets; the stored X is the free spot's centre minus half the width (the widget is drawn from
  its left edge); `PJTTransitionBranch.concentric` / `.bundle` annotated as `X | None` (they already
  returned `None`).
- 2026-10-25: [USER] new table `pjt_pegboard_sections` for the widget's position and size; one row per
  concentric; a widget attaches to a bundle or a transition; a connected bundle and branch share ONE
  widget. Name, depth (`SECTION_DEPTH_Y` = 49.0, just under the wire tables) and default size (120 x 60
  mm) are my choices and easy to change.
- 2026-10-25: [USER] asked for the `pjt_concentrics` schema bug to be corrected in
  `create_database`. `bundle_id` is now nullable (`default="NULL"`), like `transition_branch_id`;
  nothing else in the three concentric schema files needed changing (fillers are real wire rows --
  `PJTWire.is_filler_wire` -- so `pjt_concentric_wires.wire_id` stays NOT NULL). The sibling
  `harness_designer_database` repo's `pjt_*` copies are old never-built copies (MEMORY.md) and were
  left alone.
