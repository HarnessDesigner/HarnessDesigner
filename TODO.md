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

- Add TE Terminals to the database. Also find out why the solid deutsch 
    terminals are missing from the JSON file.  

- **Wire fully hidden when placed in a bundle, even the parts outside the
  bundle's own start/stop waypoints** (`objects/wire.py`,
  `database/project_db/pjt_wire.py`, `gl/canvas_pegboard` rendering). When a
  wire is placed into a bundle, the bundle's own start/stop points get
  married to waypoints *on* the wire (existing, or added at that time) — not
  the wire's own true start/stop. The wire's whole visibility flag is set to
  hidden as a result, but a wire can extend beyond the bundle's own waypoint
  boundaries (bare sections before/after where the bundle actually
  starts/stops), and those exposed sections should still render. Needs logic
  to determine at which waypoint a wire exits the bundle and render just the
  non-bundled sections instead of hiding the whole wire. Noted 2026-08-13,
  explicitly deferred by the user — fix later.

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
