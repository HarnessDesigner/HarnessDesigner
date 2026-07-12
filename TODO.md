# TODO / Noticed Issues

Running list of things noticed in passing while working on other tasks —
not necessarily in scope for whatever was being worked on at the time, but
worth coming back to. Newest entries go at the bottom of their section.

Format per entry: what/where, why it matters, and (if known) what the fix
would look like. Remove an entry once it's actually fixed or confirmed to
be intentional/non-issue.

## Open

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
