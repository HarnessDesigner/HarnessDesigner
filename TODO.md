# TODO / Noticed Issues

Running list of things noticed in passing while working on other tasks —
not necessarily in scope for whatever was being worked on at the time, but
worth coming back to. Newest entries go at the bottom of their section.

Format per entry: what/where, why it matters, and (if known) what the fix
would look like. Remove an entry once it's actually fixed or confirmed to
be intentional/non-issue.

## Open

- **Safe point-deletion / ownership design spec (given verbatim by the
  user, 2026-09-02) -- not started, captured before implementing so it
  survives context compaction.** Grew out of the wire-add-to-terminal bug
  (`PJTWire.delete()` was deleting a terminal's own shared back-routing
  point when a wire got deleted, orphaning the terminal's `wire_point3d_id`
  -- see the "Resolved" section below once this lands, and the schema
  audit entries already done 2026-09-02 for the full column inventory).

  **Ground rule already implemented:** no object's own `delete()` method
  is ever allowed to delete a `pjt_points3d`/`pjt_points2d`/
  `pjt_points_pegboard` row directly (`PJTWire.delete()`/`PJTBundle.delete()`
  fixed 2026-09-02 to stop doing this). Points are only ever removed by a
  future project-wide orphan sweep (not written yet -- run at project
  close or on an interval) that checks whether *anything* still
  references a point before deleting it.

  **Still to design/implement -- the actual "is this point safe to
  delete" check, and the cascade-delete rules between OBJECT rows (never
  point rows) that the sweep and delete() methods need to respect:**

  1. **Implementation shape (per the user):** the check has to live on
     the point row classes themselves (`PJTPoint3D`/`PJTPoint2D`/
     `PJTPointPegboard`), and it has to use real SQL so all the
     information needed for one point can be pulled in one round trip --
     not N separate `.select()` calls across ~20 tables per point.
  2. **Two distinct reference shapes to check:**
     - **Forward FK columns** -- a table has a named column pointing at
       a point's id (the full inventory of these, all ~70 columns across
       ~20 `pjt_*` tables, was catalogued and made schema-complete
       2026-09-02 -- see the two schema-audit TODO entries above/below
       this one... actually see git history/MEMORY.md for that pass,
       since this entry doesn't re-list them).
     - **Backward, count-unknown references** -- the *point itself*
       carries the tag, because the owner can have an unknown number of
       these and there's no fixed column to name each one:
       - Wire waypoints: `pjt_points3d/2d/pegboard.wire_id` (+`idx`) on
         the point row itself, pointing at `pjt_wires`.
       - Bundle waypoints: same shape, `bundle_id` pointing at
         `pjt_bundles`.
       - Transition branches: not a point-level tag, but the same
         "unknown count of children" shape one level up --
         `pjt_transition_branches.transition_id` points backward at the
         owning `pjt_transitions` row (a transition has no fixed list of
         branch columns); each branch row then has its own ordinary
         forward-referencing points (`point3d_id`/`point_pegboard_id`/
         `table_point_peg_id`), already covered by the forward-FK case.
         (Confirmed 2026-09-02: `PJTTransitionBranch` has no custom
         `delete()` at all, so it doesn't have the same "deletes its own
         shared point" bug `PJTWire`/`PJTBundle` had -- nothing to fix
         there, just noting it for the safety-check design.)

  3. **Ownership model, with the user's own worked examples verbatim:**
     A point can be *owned* by one entity (whichever entity's column is
     where the point was originally created/persisted) while being
     *borrowed*/shared by others. Ownership drives which OBJECT rows
     cascade-delete together -- it never means the point itself gets
     deleted as part of that cascade.

     - **Cover/Housing:** "a cover is attached to a housing point and if
       the housing is deleted the cover should be deleted as well. BUT
       the cover is able to be deleted separately from the housing and
       when it is deleted its position should not be deleted because the
       housing technically owns that position." -- i.e. `PJTHousing`
       owns `cover_point3d_id`; `PJTCover.point3d_id` is the same shared
       point id. Housing delete -> cascade-delete the cover row. Cover
       delete (standalone, housing untouched) -> never delete the shared
       point.
     - **Wire/Terminal (2 owned points):** "when deleting a wire we have
       to be careful of the attachment points to a terminal. There are
       actually 2 of them, one is a waypoint that has a layout and the
       other attached at the end of the wire. In this case the terminal
       owns both of those positions so they should not be deleted." --
       `PJTTerminal.attach_point3d_id` (the crimp point, reused directly
       as the wire's own start/stop) and `PJTTerminal.wire_point3d_id`
       (the back-routing point, tagged as an interior waypoint with its
       own `WireLayout` marker). Both terminal-owned; a wire delete must
       never delete either (already true today since wire delete never
       touches points at all -- this example is about *why*, for when
       the real safety-check/sweep logic gets written).
     - **Wire/Terminal-in-Cavity (a 3rd point):** "When a wire is
       attached to a terminal inside a housing there is an additional
       waypoint attachment and that is to the cavity. this position is
       owned by the cavity and should not be deleted." --
       `PJTCavity.wire_point3d_id`, also tagged as an interior waypoint
       on the wire when the terminal is seated in a cavity. Cavity-owned,
       same never-delete-on-wire-delete rule.
     - **Housing delete cascade, wires survive, points survive, stripped
       ends revert:** "When a housing is deleted all terminals and
       cavities inside the housing should also be deleted and if there
       are wire attached then the points do not get deleted because they
       are needed for the wires. The stripped ends on the wires need to
       revert back to a normal wire end as well." -- Housing delete
       cascades to its own `PJTCavity`/`PJTTerminal` rows (they get
       deleted along with it), but any `PJTWire` attached to one of those
       terminals is NOT deleted -- it survives, now dangling. The
       terminal-/cavity-owned points that wire was using as its own
       start/stop/waypoints must survive too (this is really just the
       general "never delete a point on cascade" rule again, but stated
       here because the *owning* row is what's being deleted this time,
       not the wire). New requirement, not yet designed: whatever visual/
       state concept currently makes a wire's end look "stripped"/crimped
       (searched 2026-09-02 -- no existing `stripped`/similar column or
       rendering flag found anywhere in `objects_3d/wire.py`,
       `objects_3d/terminal.py`, or the `pjt_wires` schema; this appears
       to be new behavior, not an existing feature with a bug) needs to
       revert that end to a plain/normal (non-attached) wire end once its
       terminal is gone this way. Needs clarification: is this purely a
       render-time derived state (wire end already "looks stripped"
       whenever `start_position3d_id`/`stop_position3d_id` happens to sit
       on a terminal's own attach point, so reverting is automatic once
       the wire's own start/stop point id is repointed away) or does it
       need an explicit persisted flag/column?

  4. **Not yet given -- still gathering:** cascade-delete rules for other
     object types beyond housing/cavity/terminal/wire/cover (seals,
     boots, cpa/tpa locks, splices, transitions, transition branches,
     bundles, wire service loops), and the exact SQL query shape for the
     consolidated forward-FK check. Do not start implementing the
     safety-check methods or any cascade-delete rewiring until the user
     confirms the spec is complete.

- **Peg-board editor is meant to become the same view as 3D, just with an
  orthogonal camera (design direction given by the user, 2026-09-02)** --
  the peg-board editor was originally going to be its own simplified
  representation (e.g. `objects_pegboard/splice.py`'s `Splice` rendering
  a splice as one freely-rotatable anchor point, not the start/stop-pair
  connector geometry `objects_3d/splice.py`'s `Splice` derives from the
  two/three wires it joins). The user has since shifted direction: the
  peg-board view should become the same thing as the 3D view -- same
  geometry/connector logic -- with only the camera swapped to orthogonal
  projection instead of perspective. Not started. `PJTSplice` now has the
  schema/property parity needed for this (`StartStopPositionPegboardMixin`
  + `branch_position_pegboard`, mirroring the 3D `start/stop/branch_position3d`
  trio -- added 2026-09-02 as part of a broader project_db pegboard-column
  audit), but `objects_pegboard/splice.py` itself still renders the old
  single-anchor way (temporarily re-pointed at `start_position_pegboard`
  so it doesn't crash, not reworked to the connector geometry). Likely the
  first candidate to actually rework once this is picked up, since it's
  the one object type where the two rendering models most visibly diverge
  today -- but confirm with the user whether other `objects_pegboard/*`
  types (housing/terminal/transition/wire/bundle) need the same treatment
  or already match closely enough.

- **Seal placement design spec (given verbatim by user, 2026-08-31)** --
  audit `objects/objects_3d/seal.py` (`Seal.start_add`) and
  `add_handlers/editor_3d/seal.py` against this and fix any deviation.
  Currently investigating; this is the full spec as given, captured
  before doing anything else so it isn't lost to context compaction
  mid-audit (see MEMORY.md's own "write down a detailed verbal spec
  immediately" lesson).

  A housing has one seal type. **MAT** is whichever type is NOT one of:
  dummy terminal, plug, sws, single wire seal (sws and "single wire
  seal" may be the same type named two ways -- confirm against the DB
  enum).

  Two housing-level entry points:
  1. **Right-click housing -> "Add Seal" context-menu item.** Only
     appears/is enabled when the housing's seal type is MAT (not one of
     the 4 listed above) AND the housing's own `sealing` column is
     true. Places a MAT seal.
  2. **Housing selected -> "Seal" toolbar/panel button.** Available
     regardless of the housing's seal type. Behavior depends on what
     part the user picks in the search dialog:
     - **Dummy terminal or plug** selected -> snap points are the
       housing's own CAVITIES (empty ones only -- a cavity already
       occupied by a terminal is not a valid snap target). Highlight
       candidate cavities.
     - **SWS / single wire seal** selected -> snap points are
       TERMINALS that are seated in a cavity (never bare cavities).
       For each candidate terminal: compute the size of the wire(s)
       attached to it (wire's `od_mm`), compare against the seal's own
       opening/ID size. Mismatch (opening too large or too small for
       the wire) is NOT a placement-blocking error -- still snappable
       -- but highlight that terminal RED to flag the issue. A
       terminal with no size issue gets a distinct highlight color
       that is NOT green (green is already used for housing
       selection) -- pick something else.
     - **Any other type** (i.e. MAT) selected -> instant snap to the
       housing's own seal location, no interactive cavity/terminal
       session (matches the existing Mode 1a "housing only,
       not-for_cavity" docstring in add_handlers/editor_3d/seal.py).

  Cavity-level entry point: right-click cavity -> "Add Seal" in its
  context menu.
  - Cavity is EMPTY -> part-search dialog's initial results should be
    seals of type plug or dummy terminal only.
  - Cavity HAS a terminal seated -> initial results should be seals of
    type sws or single wire seal only.
  - Both terminals and housings have their own `compat_seals` concept
    (mirrors `compat_terminals`) -- when a compat_seals list exists on
    the relevant terminal/housing, USE THAT to populate the initial
    results INSTEAD OF (takes priority over) filtering by seal type.
    Type-based filtering above is the fallback when compat_seals is
    empty/unset.

- **`Config.layout`/`wire_routing` naming mismatch** in `auto_arrange.py`/
  `housing_layout.py`/`wire_routing.py` (they reference `Config.layout.*`,
  but no `layout` class exists in `config.py` -- the real class is named
  `wire_routing`, and even that's missing a `wire_spacing` attribute
  `auto_arrange.py` needs). Deliberately NOT fixed -- the user said not
  to worry about the auto-arrange subsystem, it's getting redone later
  (2026-08-20).

- **Schematic housing/cavity/terminal layout, part 2 -- cavity AABB +
  terminal bracket/wire-stub, now BUILT (2026-08-20)** -- confirmed via
  a diagram plus concrete example coordinates from the user, which
  resolved every sign-convention ambiguity from the first pass (several
  earlier back-and-forths on this had the Z-axis/inside-outside
  direction backwards). Implemented:
  - `Housing.get_cavity_aabb` narrowed to sit INSIDE the housing (was
    spanning the full width) -- near edge at the pin edge, far edge
    short of the housing's own far edge (room for the corner label).
  - New `Housing.get_max_cavity_name_width()`.
  - `Config.object_sizes.pin_edge_padding = 3.0` -- ONE shared padding
    constant (confirmed by the user, not split per-purpose) driving the
    cavity name's own offset outside the pin edge, the terminal name's
    inset from the cavity AABB on all 4 sides, and the "(" bracket's
    offset outside the pin edge. Replaced the old, now-removed
    `cavity.name_offset`/`cavity.name_gap`/`terminal.bracket_font_size`/
    `terminal.position_outside_offset` fields.
  - `objects_schematic/terminal.py` fully rewritten: name shrink-to-fit
    (multi-line via explicit `\n`, never exceeds the configured max,
    shrinks only if needed to fit the padded AABB), the "(" bracket
    (independent sizing from `cavity_height - cavity_name_char_height`,
    positioned below the name, right-aligned to the SAME `pin_edge -
    padding` x the cavity name uses), and the wire-stub cylinder
    (starts at the "("'s own left edge, Z-centered on the "("'s height,
    length reaches `Housing.get_max_cavity_name_width()`, diameter
    `Config.object_sizes.wire.diameter`). Own `render()` override
    (swaps `_vbo`, and for the cylinder pass only `_angle`/`_scale`/
    `_position`, matching the established Wire/Housing swap idiom).
    Position is now PULLED live from the housing each render (not
    pushed via `position2d` the way every other schematic object works)
    -- `position2d`/`angle2d` still get pushed by
    `Housing._layout_children` and still matter, but only as the
    *trigger* for `_update_position`/`_update_angle` to re-derive
    everything, not as the literal anchor value.

  **Found but NOT yet wired up**: `database/project_db/pjt_terminal.py`
  has a `wire_position2d_id` field -- per `objects/terminal.py`'s own
  docstring (~line 102), this is meant to be "the far end of [the]
  wire-stub line, past every cavity name in the housing," i.e. exactly
  where a wire actually attaches -- distinct from `position2d_id` (the
  name anchor). The new cylinder's own computed stop point
  (`Terminal._cylinder_local_stop` in the schematic view) is purely
  visual right now and does NOT get persisted to
  `db_obj.wire_position2d_id`. Needs wiring up before wire-drawing can
  actually use it, but wasn't done as part of this pass -- flagged
  rather than guessed at, since writing to that DB field could affect
  the wire-drawing tool's existing behavior.

  **Not yet visually verified** -- this entire multi-message design (Z
  sign convention, inside/outside placement, padding relationships) was
  worked out and implemented without ever actually rendering it. Given
  how many corrections the sign/direction conventions alone needed
  through pure discussion, render this in the schematic editor and
  check it against the diagram before trusting it further.

  Original spec, for reference:

  1. **`Housing.get_cavity_aabb` is INSIDE the housing** -- its near
     edge sits flush at the housing's own pin edge (`pin_local_x`),
     extending inward toward the housing's far edge, but stopping
     short of it so there's always room for the corner label at the
     bottom row (kept uniform across every row for alignment, even
     though only the bottom row actually needs the clearance). This is
     a layout/bookkeeping region, not something drawn directly.
     Current code has this backwards (spans the full housing width) --
     needs narrowing.
  2. **Cavity name text is unaffected** -- it already renders entirely
     OUTSIDE the housing, disjoint from the AABB, right-aligned so its
     own right edge lands `padding` short of the AABB's near edge
     (`objects_schematic/cavity.py`'s existing
     `_sync_vbo_transform`/`_local_text_corners` already do exactly
     this -- no change needed there). Right-alignment exists
     specifically because of this "text ends at a fixed edge" rule.
  3. **Terminal's name renders INSIDE the cavity AABB** (from
     ``Housing.get_cavity_aabb``), padded on all 4 sides by a hardcoded
     value (exact number TBD -- placeholder for now, "sort out later").
     Font size starts at (never exceeds) the configured max
     (``Config.object_sizes.terminal.name_font_size``, 3.0mm) but must
     shrink below that if, at the max size, either the (single-line)
     text would extend past the padded AABB's right edge, or -- if the
     name is multi-line -- the summed height of all lines would exceed
     the padded AABB's height. (Multi-line splitting mechanism itself
     not specified -- assuming explicit newlines in the name string,
     not auto-wrap, unless told otherwise.) Not yet built -- this is
     the "terminal font is a maximum, not a constant" shrink-to-fit
     behavior flagged as an open question back when `object_sizes` was
     first introduced.
  4. **The "(" bracket is a fully separate piece from the name** --
     independent sizing AND position:
     - Size: font size dictated by
       ``cavity_height - cavity_name_max_char_height`` (the vertical
       space left over after the cavity name's own max glyph height,
       both computed the same ``shapes.text.CHARACTER_HEIGHT *
       font_size`` way ``Housing.__init__`` already computes
       ``cavity_height`` itself) -- the "(" MUST fit within that
       remaining height, so its font size has to be derived (solved
       for) from that remainder, not read off any config value.
     - Position: rendered BELOW the (already-positioned) terminal name,
       its own right edge aligned with the terminal name's own right
       edge.
     Not yet built.
  5. **New wire-stub cylinder decoration**: starting from the "("
     character's own left edge, vertically centered within the "("'s
     own height, a cylinder extends horizontally past the longest
     cavity name's own length among ALL cavities in this housing (so
     every terminal's wire-stub in a given housing is the same length,
     long enough to clear whichever cavity name is longest) --
     diameter 1.0 (matches the fixed ``Config.object_sizes.wire.diameter``
     convention already used for 2D wires). Not yet built.

  All 5 of the above are now built -- see the summary at the top of
  this entry.

- **Schematic housing/cavity/terminal rendering + layout redesign** (spec
  given 2026-08-20, mid-implementation of the objects_schematic render()
  pipeline fixes). Full design as given, not yet built:

  1. **Rendering ownership split** -- each ``objects_schematic`` class draws
     only its own piece, via its own ``render(faces_program, edges_program,
     vertices_program)`` override (matching ``BaseVar``'s current 3-arg
     contract -- this folds into the existing signature-fix work on
     ``cavity.py``/``terminal.py``/``wire.py``, and retires the dead
     ``render_extras()`` methods entirely rather than reviving them):
     - ``Housing`` renders ONLY the housing rectangle body + the housing's
       own corner label (name/part number/manufacturer).
     - ``Terminal`` renders the terminal's own name AND the "(" bracket
       (currently split across ``render()``/dead ``render_extras()`` --
       merge into one ``render()``).
     - ``Cavity`` renders ONLY its own name.
     - Default orientation: terminals (a term that includes cavities here)
       on the housing's left side, stacked vertically.

  2. **Font-size-driven sizing** -- stop hand-tuning separate font
     sizes/offsets/gaps per object type; derive as much as possible from
     font size alone, using a real measured character-height ratio rather
     than a guessed constant:
     - ``shapes/text.py``: track the tallest glyph height measured across
       every character/style built in ``build_chars()`` (at font_size=1.0,
       same ``dims.y`` ``_build_char()`` already computes) into a new
       module-level ``CHARACTER_HEIGHT`` constant, set once during the
       preload pass.
     - New font sizes: housing corner label = 3.0mm, terminal name =
       3.0mm, cavity name = 1.5mm (scaled for the project's 1mm fixed 2D
       wire size). Terminal's 3.0mm is a MAXIMUM, not a constant -- a
       given terminal's actual rendered font size must be shrunk (not yet
       specified how far, or exactly what "total text extent of all
       lines" means here -- needs clarification before implementing this
       part specifically) so its text fits within the cavity_height slot;
       cavity_height itself is always computed from the 3.0mm maximum,
       not from any shrunk per-instance value.
     - Per housing, computed once in ``Housing.__init__`` (bottom-layer
       ``objects/housing.py::Housing``, not the schematic view class) and
       cached for cavities/terminals to read without recomputing:
       ```python
       num_cavities = len(db_obj.cavities)
       terminal_font_height = _text.CHARACTER_HEIGHT * Config.editor_schematic.object_sizes.terminal.name_font_size
       self.terminal_font_height_padding = terminal_font_height * 0.1
       self.cavity_height = terminal_font_height + (self.terminal_font_height_padding * 2)
       housing_width = Config.editor_schematic.object_sizes.housing.width + (Config.editor_schematic.object_sizes.housing.width / 2)
       # +1 accounts for padding at both ends of the vertical cavity stack
       scale = _point.Point(housing_width, 1.0, self.cavity_height * (num_cavities + 1))
       ```

  3. **Natural-sort cavity ordering** -- replace the current plain
     string sort (``key=lambda c: c.name``) with a digit-run-aware natural
     sort so ``"2"`` sorts before ``"10"``:
     ```python
     _DIGIT_RUN = re.compile(r'(\d+)')

     def _sort_cavities(cavities: list[str, PJTCavity]):
         def _natural_sort_key(name: str) -> tuple:
             return tuple(
                 (0, int(chunk)) if chunk.isdigit() else (1, chunk.lower())
                 for chunk in _DIGIT_RUN.split(name) if chunk)
         return sorted(cavities, key=lambda c: _natural_sort_key(c[0]))
     ```

  4. **Cavity position lookup** -- a ``Housing`` method every
     cavity/terminal calls (rather than ``Housing._layout_children``
     pushing position2d out to each child as it does today) to derive its
     own Z-offset within the vertical stack:
     ```python
     def get_cavity_position(cavity: PJTCavity):
         index = self._cavities.index(cavity)
         padding = self.cavity_height / 2
         return (index * self.cavity_height) + padding
     ```
     Cavity name position, terminal name position, AND a terminal's wire
     attachment point are all derivable from this same cavity position
     (exact per-type X-offset math from it not yet worked out).

  5. **Batch cavity/terminal name query** -- a housing can have several
     hundred cavities; querying each cavity's own ``name`` + its
     ``terminal`` reverse-lookup + that terminal's own ``name``
     individually is 3 queries x N cavities. The batch query already
     exists and is unused --
     ``database/project_db/pjt_cavity.py:303``'s
     ``PJTCavitiesTable.names_with_terminals(housing_id)`` returns
     ``(cavity_id, cavity_name, terminal_id, terminal_name)`` for every
     cavity in one query, and its own docstring already names the
     intended (but never built) consumer:
     ``objects_schematic/housing.py``'s ``Housing._collect_names``. Needs
     to actually be called from the bottom-layer ``objects/housing.py``'s
     ``Housing`` (before per-cavity/terminal view objects are
     constructed -- see ``_construct_cavities``), with each result row's
     name(s) pre-seeded directly into the cavity's/terminal's own
     ``NameMixin._stored_name`` cache (see the "Cython typing + DB cache
     convention" memory entry's ``_stored_*`` cache pattern) so the
     later, per-object ``.name`` property read never fires its own query.

  Not started yet -- captured here mid-conversation per the "write the
  spec down immediately" rule so it survives if the session compacts.
  Open question before finishing part 2: what exactly triggers a
  terminal's own font-size shrink, and by how much/to what floor.

- **`PJTCavity.seal_position3d` vs `seal_position3d_id` read different rows**
  (`database/project_db/pjt_cavity.py`). `seal_position3d` returns
  `self.terminal_position3d` (the cavity's own `terminal_point3d_id` slot),
  but `seal_position3d_id` returns `self.terminal.position3d_id` (the
  terminal's *own* point row). These are two different `pjt_points3d` rows
  unless something else keeps them in sync. Worth confirming which one
  callers actually expect and fixing the mismatch.

- **`PJTCavity._update_angle3d`'s per-cavity rotate doesn't reach a
  terminal's own seal** (`database/project_db/pjt_cavity.py`). Its
  `accessory = self.terminal or self.seal` line is fine re: mutual
  exclusivity (a cavity can't have both a cavity-level seal and a terminal
  at once), but it never checks `self.terminal.seal` — so an SWS seal
  attached to a terminal doesn't get moved/rotated when a *single* cavity
  is rotated directly (as opposed to a whole-housing rotate, which now
  handles this correctly via `PJTHousing._update_angle3d`, fixed
  2026-07-10).

- **`PJTHousing._update_position3d` doesn't move cavity-level or
  terminal-attached seals** (`database/project_db/pjt_housing.py`). The
  position batch only collects `cavity.terminal_position3d` +
  `terminal.position3d` (+ wire attach point) when a cavity has a terminal.
  A seal's own independent `position3d` (created by
  `handlers/seal_handler.py`'s `set_part()`, Modes 2/3) is never included,
  so a seal likely doesn't follow a housing move today, only a housing
  rotate (fixed 2026-07-10, angle only). Needs the same terminal/seal
  mutual-exclusivity-aware collection added to the position batch that
  `_update_angle3d` now has.

- **`TableBase.__getitem__`/`__contains__` int-lookup pattern does a
  container-existence query, then a *separate* query for whatever property
  is read first** (`database/global_db/bases.py`, and copy-pasted into
  nearly every entity table's own `__getitem__` override — seal.py,
  terminal.py, housing.py, cavity.py, model3d.py, etc.). The pattern is:
  `if item in self: return Entry(self, item)`. `item in self` is one query
  (`SELECT id FROM table WHERE id = ...`); `Entry(self, item)` itself is
  free (lazy, no query at construction); but the *next* thing a caller
  usually does — read a property — fires that property's own
  `_stored_X`-guarded `select()`, a second query. Confirmed with the user
  (2026-07-12) that a trivial inline of the existence check (replacing
  `item in self` with a direct `select()` call) does **not** help — it's
  the exact same single query, just skipping the `__contains__` method
  hop. The only way to actually cut a query here is for `__getitem__` to
  fetch more than just `id` in that one query and pre-seed the entry's
  `_stored_X` caches from it, so the first property read doesn't need its
  own round trip.

  Explicitly held off on implementing this (2026-07-12) — decided it needs
  an audit first, not a blind fix. Before doing the real prefetch work,
  need to determine, per entity class:
  - What columns/relationships it actually has (own columns vs FK-derived
    nested objects, e.g. `manufacturer`, `color`, `cavity_lock`).
  - Which of those are read on essentially every load for an operational
    reason (software-driven — e.g. whatever the 3D editor/handlers touch
    just to render or place a part), vs which are only read when a user
    opens a specific detail/edit panel (e.g. `temperature` — likely only
    touched when the user opens that tab).
  - For the "always read operationally" set, prefetching more of the row
    (or even the FK'd object's row via a JOIN) in the initial query is a
    clear win. For the "only-if-the-user-opens-this-panel" set, eagerly
    prefetching would do *more* total work than the current lazy
    per-property queries, not less — especially if that turns into blind
    `SELECT *` or JOIN-everything across every nested relationship.
  - Whether a single `SELECT *` on the entity's own table is enough, or
    whether some hot paths need a JOIN to pull a directly-nested FK object
    in the same round trip.

  The fix, once the audit gives real access-pattern data, would be a
  generic "construct entry with pre-seeded cache" mechanism on
  `EntryBase`/`TableBase.__getitem__`, applied selectively per entity based
  on what the audit says is actually hot — not applied uniformly.

- Add TE Terminals to the database. Also find out why the solid deutsch 
    terminals are missing from the JSON file.  

- **Wire/bundle "leader" feature — bundle should stop short of the wire's
  real ends, wire should render its exposed leader sections instead of
  being fully hidden** (`handlers/bundle_handler.py`, `objects_3d/wire.py`,
  `objects_3d/bundle.py`, `objects_pegboard/wire.py`,
  `objects_pegboard/bundle.py`, likely `config.py`). Confirmed by reading
  the actual current code (not just inferred): this doesn't exist anywhere
  today, in either editor, and it's not just an unrendered gap — the data
  relationship itself doesn't support it yet:
  - `AddBundleHandler._create_preview`/`release_capture`
    (`handlers/bundle_handler.py`) seeds a new bundle's start/stop at the
    wire's own `start_position`/`stop_position` numpy values, then
    `.attach()`-*merges* the wire's start/stop Points with the bundle's —
    after creation they are literally the same Point instance, not two
    independent positions that happen to coincide. There is no margin/inset
    concept anywhere in this path.
  - `Bundle.add_wire()` (`objects_3d/bundle.py`) sets `wire.is_visible =
    False` unconditionally — the whole wire disappears for its entire
    length, not just the covered middle.

  **Full spec, given by the user 2026-08 (during the pegboard object-file
  review pass):**
  1. Add a new, user-adjustable **wire leader length** config setting.
  2. When a bundle is created over a wire (`AddBundleHandler`), the
     bundle's start/stop must no longer be `.attach()`-merged with the
     wire's own start/stop — they need to be independent points, each
     inset from the wire's real end by the leader length (so the bundle
     stops short of the wire's actual endpoint by that distance).
  3. When an existing wire is dragged onto an existing bundle:
     - If the wire's near end is **free** (not attached to a terminal/
       anything else), **shorten the wire itself** so it ends exactly one
       leader-length past the bundle's edge.
     - If the wire's near end **is** attached to a terminal, the wire's
       endpoint can't move — instead **adjust the bundle's length** to
       reach appropriately, and the leader-length rule does not apply in
       this case (the bundle just extends/shrinks to meet the wire where
       it actually is).
  4. Wire rendering (both editors) then needs to render only the leader
     sections outside wherever the bundle actually starts/stops along it,
     instead of the current unconditional `is_visible = False`. Explicit
     correction from the user: **`is_visible` is not the mechanism** —
     don't toggle the whole wire on/off. The wire's own render path needs
     to determine which part of its length falls inside the bundle's span
     and which falls outside, and draw only the outside (leader) portion
     — an inside/outside split per render, not a whole-object visibility
     flag.
  5. Explicitly scoped to build in **both editors at once** (3D and
     pegboard), not 3D-first-then-port — the user's own call when this was
     discussed.

  Not started. This is a real design/data-model change (decoupling the
  attach()-merge, adding the leader-length setting, teaching the creation/
  drag-attach handlers the shorten-wire-vs-grow-bundle branch, then
  rendering the leader sections in both editors), not a quick fix — plan it
  as its own dedicated task.

- **Rename `position2d`/`position3d` (and `angle2d`/`angle3d`) to
  `position_schematic`/`position_3d` (`angle_schematic`/`angle_3d`)**
  (`database/project_db/mixins/position2d.py`, `position3d.py`,
  `angle2d.py`, `angle3d.py`, and every column/property name derived from
  them across every `project_db` class that uses them). Continues the same
  renaming direction as `objects2d`→`objects_schematic` / `objpeg`→
  `objpegboard` done earlier (2026-08-12) — the database layer's column and
  property names should match that convention too. Update the underlying
  SQL column names in the `database/create_database/` schema files as well,
  not just the Python property/attribute names. Noted 2026-08-13 by the
  user, explicitly deferred — large, mechanical, cross-cutting rename, not
  part of the current pegboard database work.

- **No orphaned-point cleanup for `pjt_points3d`/`pjt_points2d`/
  `pjt_points_pegboard`** (`database/project_db/`). Deleting a row that
  references a point (a wire, a housing, a layout, etc.) deliberately does
  NOT delete the point row it referenced — this is intentional, not an
  oversight, to avoid an extra DELETE query on every referencing-row
  deletion. Instead, orphaned points (rows in a points table no longer
  referenced by anything) are meant to be cleaned up in a batch sweep when a
  project closes — scan all three points tables, scoped by project id, for
  rows nothing currently references, and delete them in bulk. This sweep
  has not been written yet. Noted 2026-08-13 by the user — future work, not
  part of the current pegboard database work.

- **`PJTBundle.delete()`'s BundleLayout cleanup queries the wrong column
  name** (`database/project_db/pjt_bundle.py`). The 3D branch does
  `layouts_table.select('id', position3d_id=point.db_id)`, but
  `pjt_bundle_layouts`'s actual column is `point3d_id` (see
  `database/create_database/bundle_cover_layouts.py`) — `position3d_id`
  isn't a real column on that table, so this lookup never matches
  anything and every BundleLayout row referencing a deleted bundle's
  waypoint is silently left behind (orphaned) instead of being cleaned
  up. Noticed 2026-08-13 while adding the equivalent peg-board waypoint
  cleanup (which correctly uses `point_pegboard_id`) alongside it — left
  the existing 3D line as-is since fixing pre-existing bugs is out of
  scope for the current pegboard database work.

- **2D camera doesn't emit `GLCameraEvent` at all yet, unlike 3D**
  (`gl/canvas2d/camera.py`'s `Zoom`/`Pan`). `gl/canvas3d/camera.py`'s
  `Camera._send_event` is called at the end of every 3D camera-movement
  method and (as of 2026-08-05) also drives `_refresh_active_hover()` —
  re-running the active wire-placement handler's `hover()` or the active
  drag's pick-test after a camera move that happened with the mouse held
  still (mouse-wheel zoom, keyboard camera controls), so a preview/snap
  never reflects a stale pre-move camera framing. `GLCameraEvent.from_canvas`
  (`gl/events.py`) is already canvas-generic — nothing 3D-specific about it —
  but `canvas2d.Camera` never calls it, so 2D has neither the event
  notification nor the hover-refresh fix. Bring 2D up to parity: add
  `_send_event` calls to `Zoom`/`Pan` (matching the 3D pattern) and the same
  `_refresh_active_hover` hook, so `wire_handler_2d.py`'s preview gets the
  same fix. Confirmed with the user (2026-08-05) this is a real gap, deferred
  to this list rather than fixed immediately.

## Resolved (kept briefly for context, safe to delete)

- Terminal never actually got added to the project after part-search
  confirm — root cause was `EditorList.get_obj_id()` using Qt's 0-indexed
  row directly against SQL's 1-indexed `ROW_NUMBER()`; fixed at the
  `SearchDialog.GetValue()` call site (`ui/dialogs/part_search.py`), not in
  the shared method. (2026-07-10)
- Terminal position/angle not following housing move/rotate — terminal now
  gets its own independent `pjt_points3d` row (position formulas: female =
  cavity midpoint, male = 1/3 from forward OBB face toward wire face,
  gender resolved terminal-part → housing → default male), and
  `PJTHousing._update_angle3d` now batch-updates terminal (and its cavity's
  own seal, mutual-exclusivity aware) angles alongside cavities/accessories.
  (2026-07-10)
- Terminals/seals were directly selectable in the 3D view/context menus;
  now `Terminal.set_selected`/`Seal.set_selected` redirect to the owning
  cavity (or housing, for a MAT seal). (2026-07-10)
