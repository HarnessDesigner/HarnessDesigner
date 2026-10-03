# Boot design

Single home for boot-specific design: how a boot's shape is described,
how it renders, and how (if at all) it bends to follow the harness. Add to
this file as the design firms up; do not scatter boot design into
MEMORY.md (which only keeps a pointer here).

Last updated: 2026-09-27.

Sections:
1. Scope
2. Current code state (audit, 2026-09-27)
3. The three hard problems
4. Open questions
5. Decision log

---

## 1. Scope

A boot seals and strain-relieves the cable exit at a housing connector.
This file covers how a boot's own shape/geometry is described and rendered,
and separately, whether/how it bends to follow the actual routed bundle at
runtime. It does not cover the transition primitive-rendering design
(`TRANSITION_DESIGN.md`) or the future authoring-dialog sketch
(`TRANSITION_EDITOR_DIALOG.md`), though a boot is one of the two named
candidates for that dialog and whatever primitive vocabulary this file
settles on needs to stay compatible with it.

## 2. Current code state (audit, 2026-09-27)

Confirmed by reading the code, not assumed:

- **A boot is a single, rigid, uploaded/downloaded CAD model**, same
  mechanism housings use (`Boot.model3d`, `database/global_db/boot.py`'s
  `model3d_id`/`cad_id`). `objects/objects_3d/boot.py`'s `Boot` class is a
  plain `Base3D` -- one static `position3d`/`angle3d`, one mesh, no bending,
  no procedural geometry of any kind. There is nothing here to extend for
  either problem in section 3 -- both are new capability, not a bug fix or
  a missing parameter on an existing mechanism.
- **`direction_id`** (`database/create_database/directions.py`:
  `Unknown`/`Left`/`Right`/`Straight`/`90°`/`180°`/`270°`) is a **catalog
  variant**, not a live/dynamic angle -- a "90° boot" is a distinct
  physical part number a user stocks and picks, the same as choosing a
  90° vs. a straight backshell. It is not a mechanism for following an
  arbitrary bundle direction.
- **No shape field exists at all** for the housing-connection end (round
  vs. rectangular) -- `boots` (global DB) has `length`/`width`/`height`
  (the model's own bounding box, for scale/placement, not a
  cross-section shape) and `min_dia`/`max_dia` (the cable-exit-end
  diameter range, presumably), but nothing describing the shape of the
  end that mates to a housing.
- `shapes/box.py` already exists (alongside `cylinder.py`/`sphere.py`),
  pooled the same way -- relevant if a rectangular cross-section ends up
  needing its own primitive rather than being approximated by the
  cylinder/sphere vocabulary `TRANSITION_DESIGN.md` settled on for
  transitions (that vocabulary was explicitly confirmed cylinder+sphere
  only, for transitions -- not yet decided whether that same restriction
  should apply to boots, see section 4).
- `shapes/cylinder_helix.py` already exists -- a curved/helical sweep
  primitive. Not obviously the right tool for a bending boot, but it is
  existing precedent in this codebase for sweeping a cross-section along a
  non-straight path, worth knowing about before assuming a bending boot
  needs an entirely new rendering technique.

## 3. The three hard problems

**Problem 1: the housing-connection end's cross-section shape (round or
rectangular).** A real boot's shape at the end that mates to a housing
connector matches that connector's own face -- round for a round
connector, rectangular for a rectangular one -- and typically necks down
to a round cable exit at the other end. Representing a rectangular
cross-section is not something the transition design's cylinder+sphere
vocabulary covers; `shapes/box.py` exists and could supply it, but a boot
that transitions from a rectangular face to a round one over its own
length is a genuine shape-blend problem (a loft between two different
cross-section shapes), not just "pick box or cylinder."

**Problem 2 (flagged by the user as the harder one): the boot flexing to
follow the actual routed bundle.** A real boot is flexible rubber/plastic
and bends with however the harness is actually routed leaving the
housing -- it does not stay rigid at one fixed exit angle the way today's
model does. Making this work inside the app means the boot's own geometry
would need to react to the live bundle path near the housing (which is
itself a chain-solved polyline that can change any time the harness is
edited -- see `BUNDLE_PLACEMENT.md`'s peg-board chain-solver design),
not just sit at a fixed `angle3d` like every other rigid part. This is
qualitatively different from every other catalog part in the app today,
all of which are rigid.

**Problem 3: a boot's diameter tapers continuously along its length**, not
in discrete steps -- a real boot smoothly necks down from the housing end
to the cable end, not stepped-cylinder-and-cap-sphere the way a
transition's bulb is approximated (`TRANSITION_DESIGN.md` section 4). The
user's own assessment: rendering a smooth, correct continuous taper is
genuinely hard even with a real CAD kernel (OCP/`build123d`), not just with
the primitive approach -- so this is not a case where "use the precise CAD
tool instead" is an easy fallback the way it might be for other shapes.
Whether the stepped-cylinder-plus-cap-sphere approximation already accepted
for a transition's bulb is good enough for a boot's much longer, more
visually prominent taper, or whether a true frustum/loft approach is worth
the added complexity here, is open -- see section 4.

## 4. Open questions

All three problems are wide open; nothing below is decided.

- **For problem 2, what is actually wanted?** Two very different scopes:
  1. **Stays rigid, but richer catalog data**: a boot is still one fixed
     shape per part (as today), and "flex" really means picking the right
     stocked variant (straight/90°/180°/270°, as `direction_id` already
     half-models) -- no runtime bending at all, just better authoring/shape
     data from problem 1.
  2. **Genuinely reactive geometry**: the boot's own mesh bends to track
     the live bundle direction as the harness is routed/edited, which is a
     real deformable-geometry problem, not a data-modeling one, and would
     make a boot the first non-rigid catalog object in the app.
- If (2): does it bend continuously in real time as the bundle is edited,
  or is it computed once when the boot is placed/attached and left alone
  after that (cheaper, but stale if the routing changes later)?
- If (2): what actually drives the bend -- the bundle's own initial
  tangent direction as it leaves the housing, some fixed length along the
  boot that must match the bundle's local curvature, or something else?
- For problem 1: does the cross-section shape stay a single discrete
  choice per catalog part (round OR rectangular, like `direction_id`'s
  existing catalog-variant pattern), or does one boot need to describe a
  shape that changes along its own length (rectangular at the housing end,
  round at the cable end)?
- Does whatever shape/bend representation gets chosen here need to be
  something the future authoring dialog (`TRANSITION_EDITOR_DIALOG.md`)
  can actually produce, or is a bending boot out of scope for that tool
  even if boots in general are in scope?
- For problem 3: is a stepped-cylinder-plus-sphere approximation (more,
  shorter steps for a smoother look, if needed) an acceptable trade-off,
  or does a true continuous taper (a real frustum primitive, or a lofted
  cross-section sweep) matter enough visually to be worth pursuing despite
  the user's own note that it's hard even in a real CAD kernel?
- Do problems 2 and 3 interact -- does a tapered AND bending boot need a
  single combined representation (e.g. a swept profile along a curved
  spine, varying radius along that spine), rather than solving each
  independently?

## 5. Decision log

- **2026-09-27**: file created; three hard problems named by the user
  (housing-end cross-section shape, flex/bend following the routed
  harness, and continuous taper along the boot's length) recorded before
  any solution is attempted.
