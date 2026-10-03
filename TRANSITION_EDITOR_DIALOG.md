# Transition editor dialog

Supersedes the early sketch below with a concrete, committed design as of
2026-09-27 -- the user has asked for this dialog to be built for real, in
the app (`harness_designer/ui/dialogs/transition_editor/`), not the scratch
tool under `scratches/transition_viewer/` (that tool's job -- fixing the 111
existing catalog rows -- is done; its data has been merged into the live
catalog and into `harness_designer_database`'s `Universal/transitions.json`
and builder scripts). See `TRANSITION_DESIGN.md` for the primitive-rendering
design this dialog depends on.

Sections:
1. Purpose (current)
2. Architecture discovery -- what already exists and can be reused
3. Dialog design
4. The shared primitive-rendering rewrite -- DONE, see TRANSITION_DESIGN.md
5. Branch highlighting and mouse interaction
6. Staged implementation plan (status)
7. Open question carried from the original early-stage sketch
7.5-7.8 Stages 1-3 status -- DONE, see TRANSITION_DESIGN.md
7.9 Stage 4 status: dialog shell -- first slice built, not yet launched
7.10 Placement bugs found and fixed
8. Decision log

---

## 1. Purpose (current)

An in-app dialog for authoring and correcting transition catalog parts --
both their metadata (part number, manufacturer, family, series, description,
color, material, shape, protection, adhesives, weight, resources) and their
per-branch geometry (offset, angle, length, diameters, bulb, flange) -- with
a live 3D preview using the app's real rendering pipeline, not a separate
preview renderer. Modeled structurally on
`ui/dialogs/part_orientation.py` (self-contained `Canvas3D` + side panel,
own `bounds.Manager`, own `_Config`), not on the scratch tool's ad hoc
`QOpenGLWidget`.

## 2. Architecture discovery -- what already exists and can be reused

Reading the real app code (not the scratch tool) before designing this
turned up more prior art than expected:

- **`database/global_db/transition.py`'s `TransitionControl`** (a
  `QTabWidget` + `LazyTabMixin`) is an ALREADY-BUILT, ALREADY-COMPLETE
  editor for every column on a `transitions` row: General tab (part number,
  description, color, weight, material, protection, adhesives), plus
  Manufacturer/Family/Series/Temperature/Resources tabs, each backed by the
  matching mixin's own `*Control` widget
  (`PartNumberControl`/`DescriptionControl`/`ColorControl`/`WeightControl`/
  `MaterialControl`/`ProtectionControl`/`AdhesiveControl`/
  `ManufacturerControl`/`FamilyControl`/`SeriesControl`/`TemperatureControl`/
  `ResourcesControl`). It also already has a **"Branches" tab**: a
  `branch_count` spinner (1-6) and a nested `QTabWidget` with one
  `TransitionBranchControl` per branch -- i.e. **the notebook-per-branch
  interface the user asked for already exists**, added/removed
  automatically as `branch_count` changes (`_on_branch_count`).
- **`database/global_db/transition_branch.py`'s `TransitionBranchControl`**
  (a `_prop_ctrls.Category`) already has spin controls for length,
  `angle` (`AngleProperty`, already 3-axis xyz -- this file was already
  updated for the euler migration), `offset` (`PositionProperty`, xyz),
  bulb offset/length, min/max diameter, **and flange height/width** (the
  spin controls the user asked to add -- they're already there,
  `flange_height_ctrl`/`flange_width_ctrl`, wired to the DB column). Nothing
  needed adding for flanges on the *data-entry* side; only the primitive
  *renderer* (section 4) doesn't draw them yet.
- **Bug found and fixed while reading this** (2026-09-27, same session):
  `TransitionBranch.bulb_offset`'s getter still read the DB text as a
  2-element list and hardcoded `z=0` -- a leftover from before this
  session's 3-axis migration (the setter already wrote all 3 components,
  so this was a read/write asymmetry). Fixed to `ast.literal_eval` all 3
  axes, matching the already-correct `angle`/`offset` getters right above
  it. See `harness_designer/database/global_db/transition_branch.py`.
- **These widgets are not currently reachable from any live 3D-preview
  context.** `TransitionsTable.control` memoizes a single shared
  `TransitionControl` instance, reparented on demand (`.hide()` when not
  in use) -- the same singleton-widget-reparenting pattern this dialog
  should follow, not construct its own competing copy. Today nothing but
  `pjt_transition.py`'s *separate* `PJTTransitionControl` (project-instance
  properties, e.g. for a placed transition's name/notes/position -- not the
  same class) references it, so there is no existing dialog that pairs it
  with a 3D view.

**Decision: reuse `TransitionControl`/`TransitionBranchControl` directly**
as this dialog's metadata + branch-field side panel, rather than
reimplementing raw `QDoubleSpinBox` forms the way the scratch tool did.
This is less code, stays visually/behaviorally consistent with every other
part-editor surface in the app (`prop_ctrls` idiom), and the scratch tool's
bespoke spin-box panel was always a throwaway stand-in for exactly this,
per its own docstring ("the real app would use its own `ui.prop_ctrls`
widgets, the way `TransitionBranchControl` already does").

## 3. Dialog design

Location: `harness_designer/ui/dialogs/transition_editor/` (new package,
multiple files -- not a single-file dialog like `part_orientation.py`,
since this one has more moving parts: the dialog shell, the primitive/VBO
model class shared with the render pipeline rewrite, and the
branch-highlight/drag-interaction handler).

**Opening the dialog** -- three entry modes, chosen up front:
1. **Select an existing transition** to edit in place (reuses
   `part_search.SearchDialog` + `TransitionsPage`, the same picker
   `Transition.start_add` already uses to add one to a project).
2. **Create a new transition** from scratch -- blank metadata, 0 branches.
3. **Load an existing transition as a template** -- same picker as (1),
   but the loaded part's `part_number` field is immediately editable (not
   the read-only-until-changed field it'd otherwise be) and **Save always
   inserts a new `transitions` row** rather than updating the source row.
   Every other field (branches, metadata) starts as a copy of the source
   part, exactly like starting from (1) and then changing the part number
   -- template mode is really just "(1) but Save targets a new row," which
   keeps this from needing a separate code path for the actual field
   widgets.

**Live preview object -- SUBCLASSES `objects_3d.transition.Transition`
directly**, per the user's own explicit correction (2026-09-27):
`part_orientation.py`'s `PartModel3D` is a from-scratch `Base3D` subclass
only because THAT dialog previews every catalog part type generically (it
has no one concrete class to reuse); it's a model for "how to use
Canvas3D as a framework," not a model for "always write a parallel
facade." This dialog deals with transitions specifically, so its preview
(`ui/dialogs/transition_editor/preview.py`'s `PreviewTransition3D`)
subclasses `objects_3d.transition.Transition` itself, overriding only
`__init__` (to source data from a catalog `Transition`/`TransitionBranch`
part instead of a placed `PJTTransition`, calling `Base3D.__init__`
directly rather than `Transition.__init__`, which it deliberately
bypasses) and `handle_interaction` (a preview should never be
click-dragged around the dialog's own scene the way a real placed
Transition can be). `build()`, `_update_angle`/`_update_position`, and
every rendering/hit-testing/AABB-OBB mechanism are all inherited
UNCHANGED. `objects_3d.transition.Branch` (the tip-marker spheres) got one
small, backward-compatible change to support this: `db_obj` may now be
`None` (a brand-new optional `catalog_branch` param supplies what
`min_diameter`/`max_diameter` would otherwise read off `db_obj.transition
.part.branches[...]`, and the `diameter` setter simply skips its DB
write-back when there's no `db_obj` to write to) -- everything else about
`Branch` is untouched. `Transition.smooth`'s getter was also made
defensive (`getattr(self.db_obj, 'smooth', None)` instead of a direct
attribute access) so it degrades the same way `BaseVar`'s own default
already does when `db_obj` has no such attribute, rather than raising.

**Layout** (mirroring `part_orientation.py`'s `h_layout`: canvas left,
controls right):
- Left: `Canvas3D` (this dialog's own self-contained scene + `bounds.Manager`,
  per `part_orientation.py`'s pattern -- not a view into the mainframe's
  live editor3d).
- Right:
  - Mode/part picker row (the three entry modes above; shows the loaded
    part number, editable only in template/new mode).
  - The reused `TransitionControl` (General/Mfg/Family/Series/Temperature/
    Resources/Branches tabs) -- this dialog calls `set_obj()` on the
    catalog's own shared instance and reparents it into its own layout,
    reparenting it back (and re-hiding it) on close, exactly like
    `TransitionControl.set_obj`'s own branch-tab reparenting already does
    for `TransitionBranchControl` instances.
  - Extra controls this dialog adds on top of the reused Branches tab
    (`TransitionBranchControl` itself is not modified beyond what section 2
    already covers):
    - **"Duplicate branch" button** next to the branch notebook -- copies
      every field of the currently-active branch tab into a newly-inserted
      branch (subject to the 6-branch cap), selects the new tab.
    - Branch-tab **selection drives a highlight color** in the 3D view (see
      section 5) -- switching the notebook's current tab is the only signal
      needed; no separate "select in 3D" step.
- **No log/output text panel** -- the scratch tool's `QPlainTextEdit`
  debug-text pane (branch field dump, build timing) does not belong in the
  production dialog; the 3D view and the bound `prop_ctrls` widgets are
  themselves the feedback loop. (Explicit user instruction, 2026-09-27.)
- **All float fields display/round to 2 decimal places** -- a uniform
  precision convention across every spin control in this dialog (length,
  angle, offset, bulb offset/length, diameters, flange height/width,
  weight), not the mixed 2-vs-3-decimal split the scratch tool had
  (`length`/diameters at 2 decimals, `offset` at 3). Applies to
  `TransitionBranchControl`'s existing `_prop_ctrls.FloatProperty`/
  `AngleProperty`/`PositionProperty` field constructions (pass an explicit
  `decimals=2` wherever the current default differs) -- and, since that
  control is shared/reused (section 2), this is a small, generally
  applicable precision fix, not something special-cased to this dialog.
  (Explicit user instruction, 2026-09-27.)

**Tab persistence across transition switches**: switching which
transition is loaded (Prev/Next, or picking a different existing part)
must NOT reset `branch_page.currentIndex()` -- if the newly-loaded part has
fewer branches than the previously-selected tab index, clamp instead of
resetting to 0. This is the concrete meaning of "retaining the currently
active tab" from the request.

## 4. The shared primitive-rendering rewrite (3D view + pegboard view + this dialog) -- DONE, see TRANSITION_DESIGN.md

The rendering rewrite this section originally designed (a shared `TransitionModel` class) was superseded one day into implementation by a simpler design the user requested -- `_BranchBody`/`_Hub`/`_Body` classes written directly in each consumer file, no shared module. `TRANSITION_DESIGN.md` sections 8.6-8.12 are the authoritative current description (3D view, pegboard view, and this dialog's preview -- `ui/dialogs/transition_editor/preview.py` -- all reuse the same `objects_3d.transition._Body`).

**Flanges**: `TransitionBranch` has `flange_height`/`flange_width` columns and UI controls (section 2); still not drawn by any renderer. Deferred, not forgotten. (Likely shape once scheduled: a flat box or short wide cylinder cap at the branch's connection end, sized by height/width -- undecided.)

## 5. Branch highlighting and mouse interaction

- **Highlighting**: the infrastructure for this now exists on `Transition` itself (`TRANSITION_DESIGN.md` section 8.11 -- `highlight_branch`/`clear_branch_highlight`/`clear_branch_highlights`/`highlight_branches_for_diameter`, backed by a `branch_materials: dict[int, GLMaterial]` and a `_render_geometry` override), built for the wire/bundle-drag fit-highlighting use case but directly reusable here: driving it off the editor dialog's branch-tab selection (section 3) instead is a wiring task in `dialog.py`/`preview.py`, not a design gap. Still not wired up (not part of the 7.9 first slice).
- **Mouse interaction / drag-drop for individual branches**: needs per-branch hit testing (`Transition.hit_test_branch`/`hit_test_branch_ray`, also already built per section 8.11, for a real world-space point or a screen-space ray respectively), then a drag handler that adjusts that branch's `offset`/`angle`/`length` live (mirroring how `add_handlers/editor_3d/wire.py` and `drag_handlers/editor_schematic/wire.py` already implement drag-to-edit for wire path points -- the closest existing precedent, not yet read in detail). This is the most open-ended, least-precedented piece of this whole design and is deliberately the LAST staged item (section 6) -- everything else (dialog shell, metadata reuse, non-interactive live preview, highlighting driven by the tab widget rather than 3D clicks) is useful and shippable without it.

## 6. Staged implementation plan

Ordered so each stage is independently useful and testable, and later
stages depend only on earlier ones. Steps 1-3's original plan named a
shared `TransitionModel` class; the actual architecture that shipped is
`_BranchBody`/`_Hub`/`_Body` per consumer file (`TRANSITION_DESIGN.md`
8.6-8.12) -- the step outcomes below are unaffected, only the class name.

1. **DONE** -- primitive instance rendering (pooled `cylinder`/`sphere`
   VBOs, centralized position/rotation), validated against all 111
   catalog parts.
2. **DONE** -- `objects_3d.transition.Transition` renders through it.
3. **DONE** -- `objects_pegboard.transition.Transition` brought to full
   parity (`TRANSITION_DESIGN.md` 8.12).
4. **FIRST SLICE DONE, not yet launched** -- dialog shell (section 7.9):
   `ui/dialogs/transition_editor/` package, canvas + reused
   `TransitionControl` panel, the 3 entry modes, tab-persistence across
   part switches -- live 3D preview, no highlighting or drag interaction
   yet, no menu/toolbar entry point wired up yet, no duplicate-branch
   button yet.
5. **NOT DONE** -- branch-tab-driven highlighting (section 5's first
   half). The underlying `Transition.highlight_branch` infrastructure
   exists (`TRANSITION_DESIGN.md` 8.11) but is not wired to the dialog's
   tab-selection signal.
6. **NOT DONE** -- per-branch mouse drag interaction (section 5's second
   half) -- deferred to last; open-ended scope, lowest confidence, and
   the dialog is already useful (numeric editing + live preview, once
   step 5 lands) without it.

## 7. Open question carried from the original early-stage sketch

One question from the pre-section-2 sketch (2026-09-27, since superseded
and removed) is still genuinely open and not answered anywhere else:

- Does a primitive-based boot definition *replace* the uploaded-CAD-model
  path for boots (`Boot.model3d`, see `BOOT_DESIGN.md`), or live alongside
  it as an alternative a user picks per part?
- What other catalog part types (besides transitions and boots) are simple
  enough, geometrically, to be worth adding to a similar dialog later?

## 7.5-7.8 Stages 1-3 and "round to 2 decimals" -- DONE, see TRANSITION_DESIGN.md

Stages 1-3 (a shared primitive rendering class, swapping the 3D editor over to it, and the pegboard view) landed as described in section 6 above; the final architecture is `TRANSITION_DESIGN.md` sections 8.6-8.12, not the `TransitionModel`/`VBOHandlerBase` design these stages were originally written against (that intermediate design was retired -- see section 4). The "round to 2 decimals" check (`ui/prop_ctrls/float_prop.py` and friends) also came back already satisfied: every field this dialog shows already rounds/steps to 2 decimal places via `increment=0.01`, no code change needed.

## 7.9 Stage 4 status: dialog shell -- FIRST SLICE built, compiles, NOT yet
## launched

New package: `harness_designer/ui/dialogs/transition_editor/` --
`__init__.py`, `dialog.py` (`TransitionEditorDialog`), `preview.py`
(`PreviewTransition`/`PreviewTransition3D`).

**`preview.py`**: `PreviewTransition3D` SUBCLASSES
`objects_3d.transition.Transition` (see section 3's note for why, and for
exactly what's overridden vs. inherited) -- built directly from a catalog
`Transition`/its `TransitionBranch` rows plus a fresh `_Body`
(`TRANSITION_DESIGN.md` 8.6+), never a `PJTTransition`. Always at the
origin, identity angle -- the inherited `build()`'s delta-transform
bookkeeping degenerates to a no-op against those, so it needs no override.
Its own `rebuild()` method is a thin wrapper: when `branch_count` changed
since the last build (this dialog's whole purpose, unlike a real
placement, is editing that), it first rebuilds `self._body.branches` to
the new length, then calls the inherited `build()`.

**`dialog.py`**: `TransitionEditorDialog(BaseDialog)`, canvas left /
controls right (`part_orientation.py`'s own layout). Three entry modes:
"Select Existing" and "Load As Template" both reuse `part_search.
SearchDialog` (the same picker `Transition.start_add` already uses) via a
shared `_pick_part()` helper; "New" inserts a bare placeholder row
(`NEW-<8 hex chars>` part number, every FK set to the schema's own
already-seeded nil-UUID sentinel row -- see `_NIL_ID`'s own docstring).
"Load As Template" clones every field AND every branch row from the
source part under a fresh, guaranteed-unique part number
(`<source>-COPY-<6 hex chars>`) via `_clone_transition()`, then loads the
clone -- so template mode really is just "select existing, but Save
targets a new row," exactly as designed in section 3. The catalog's own
shared `TransitionControl` (`mainframe.global_db.transitions_table.
control`) is reparented into this dialog for as long as it's open, and
back onto the mainframe (hidden) on close -- the same reparenting
discipline `TransitionControl.set_obj` already applies to its own
`TransitionBranchControl` children. A single Close button, no Save/Cancel
distinction -- every field edit through the reused controls already
writes straight to the database (see section 2's reuse decision), so
there is nothing this dialog's own OK/Cancel would mean beyond what
`TransitionControl` already does per keystroke.

Tab persistence across a part switch (section 3's requirement): the
dialog tracks `branch_page.currentIndex()` on every tab change and on
every `_load()`, restoring it (clamped to the new part's branch count)
after `set_obj()` repopulates the branch notebook.

Live preview: debounced (150ms, same pattern as the scratch tool) rebuild
triggered off `branch_count_ctrl.propertyChanged` for now -- **not yet
wired to the individual branch-field controls** (length/angle/offset/
bulb/diameter/flange) themselves, so editing an existing branch's numbers
won't yet refresh the 3D view live; only adding/removing a branch does.
Flagged as the very next thing to wire up, not forgotten.

**Explicitly NOT done in this first slice** (tracked, not lost):
- Wiring the individual branch field controls' own `propertyChanged`
  signals (including each `AngleProperty`/`PositionProperty`'s per-axis
  `x_ctrl`/`y_ctrl`/`z_ctrl`) to the debounced preview rebuild.
- "Duplicate branch" button.
- Branch-tab-selection-driven highlighting in the 3D view (stage 5 -- see
  section 5: `Transition.highlight_branch` and friends already exist
  (`TRANSITION_DESIGN.md` 8.11) and work on `PreviewTransition3D` since it
  subclasses `Transition`; wiring the dialog's tab-change signal to them
  is what's actually missing).
- Per-branch mouse drag interaction (stage 6).
- **No menu/toolbar entry point wired up yet** -- nothing in the running
  app currently opens `TransitionEditorDialog` at all. Needs a decision on
  where it belongs (a new toolbar button, a menu item, a right-click
  action on an existing transition) before anyone but a developer
  constructing it directly could reach it.

**Verification performed**: all three files compile cleanly. Not yet
launched in the real app -- doing that means either bootstrapping through
`run.py`'s real entry point (`harness_designer.__main__()`, which opens
the actual full application window) or a lighter, not-yet-written
standalone harness; unlike the scratch tool's own sqlite-only `Catalog`
class, this dialog goes through the real ORM layer (`TableBase`/
`EntryBase`/mixins), which hits a pre-existing circular-import ceiling
when imported standalone (this module has apparently never been
importable outside the app's own real bootstrap order). Genuine functional
verification is the clear next step, and needs either the user's own run
or an explicit go-ahead to launch the real app from here.

## 7.10 Placement bugs found while the user tested Stage 2/4 -- fixed

Three pre-existing bugs in `Transition.start_add`/placement, found while testing, now fixed: a bare `Angle()` placeholder wrote literal `"[nan, nan, nan]"` into `angle3d` (now `Angle.from_euler(0.0, 0.0, 0.0)`); and a transition branch required a `pjt_concentrics` row that nothing created for a free placement, crashing on read (`[0][0]`-on-empty-result).

**Load-bearing decision, still current:** rather than patch the concentric requirement, transitions no longer depend on concentric twisting at all -- `Transition.start_add` creates no `pjt_concentrics` row, and `PJTTransitionBranch.wires` reads the general-purpose `pjt_wire_paths` table instead (`bundle_id`/`concentric_id`/`transition_id`/`transition_branch_id` are optional tags on a row there, not a requirement). This is the answer `BUNDLE_PLACEMENT.md` section 9 item 5 points to. `PJTTransitionBranch.concentric` itself still exists (used by `ui/dialogs/transition_routing.py`, not touched here) but degrades to `None` on an empty result instead of raising.

## 8. Decision log

- **2026-09-27 (original)**: dialog concept recorded, per the user's stated
  eventual goal -- a 3D authoring tool for transitions and boots.
- **2026-09-27 (this update)**: scope narrowed to transitions only for now;
  concrete architecture chosen after reading the real (non-scratch) code:
  reuse `TransitionControl`/`TransitionBranchControl` for metadata/branch
  fields rather than rebuilding them; introduce a shared `TransitionModel`
  class (pooled-VBO primitive instances, centralized transform, per-branch
  identity) used by the 3D editor, the pegboard editor, AND this dialog's
  preview, replacing the OCC `_build_model` fused-mesh path everywhere, not
  just in the dialog. Found and fixed a real bug in the same pass:
  `TransitionBranch.bulb_offset`'s getter still truncated to 2 axes.
  User-specified UI requirements: choice of new/existing/template on open;
  notebook-per-branch tabs (already existed via `TransitionBranchControl`,
  just never paired with a 3D view); tab selection persists across
  switching which transition is loaded; a "duplicate branch" button;
  branch-tab selection highlights that branch a different color in the 3D
  view; flange spin controls (already existed, just not yet drawn by any
  renderer); no debug/log text panel (explicitly excluded, unlike the
  scratch tool). Per-branch mouse drag interaction confirmed in scope but
  staged last -- most open-ended, least-precedented part of the design.
