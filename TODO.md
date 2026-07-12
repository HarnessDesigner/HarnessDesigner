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
