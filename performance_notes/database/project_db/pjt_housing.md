# harness_designer/database/project_db/pjt_housing.py

SQL calls in this module (AST count): 63.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTHousing.cavities`: no cache guard found (queries on every read).
- `PJTHousing.wires`: no cache guard found (queries on every read).
- `PJTHousing.cover_position3d_id`: cached after first read.
- `PJTHousing.seal_position3d_id`: cached after first read.
- `PJTHousing.seal_position_pegboard_id`: cached after first read.
- `PJTHousing.boot_position3d_id`: cached after first read.
- `PJTHousing.tpa_lock_1_position3d_id`: cached after first read.
- `PJTHousing.tpa_lock_2_position3d_id`: cached after first read.
- `PJTHousing.cpa_lock_position3d_id`: cached after first read.
- `PJTHousing.seal`: no cache guard found (queries on every read).
- `PJTHousing.cpa_lock`: no cache guard found (queries on every read).
- `PJTHousing.tpa_lock1`: no cache guard found (queries on every read).
- `PJTHousing.tpa_lock2`: no cache guard found (queries on every read).
- `PJTHousing.tpa_locks`: no cache guard found (queries on every read).
- `PJTHousing.cover`: no cache guard found (queries on every read).
- `PJTHousing.boot`: no cache guard found (queries on every read).

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTHousing.wires`.


Status: static read of the code only. Nothing here has been profiled.

## `_update_position_pegboard` -- fixed, profiled (2026-10-17)
Moves every cavity/terminal/seal/wire-routing point of the housing by the same delta, one at a time, each firing `pos._process_callbacks()` separately. Several of these points belong to the SAME wire (a seated terminal's own attach point, its own stub, and its cavity's stub), so each one independently triggering that wire's full geometry rebuild (`objects_pegboard.wire.Wire._recalculate_geometry`) meant one housing move rebuilt the same wire's geometry up to three times over -- confirmed live via a logged call-stack dump (see `handlers/rope_pull_handler.md`'s "Part 6" note for the full history). Fixed by collecting every chain touching any of `all_positions` before the move loop, calling `suspend_updates()` on each, then `resume_updates()` in a `finally` -- one real rebuild per affected chain for the whole housing move, not one per point. Lazy-imports `rope_pull_handler` inside the function (that module transitively imports this whole package) -- verified safe by simulating the lazy import after the full app module graph loads, same pattern `objects_pegboard.wire.Wire._bind_waypoints` already uses for the identical reason.

**Correction (2026-10-17): the first version of the collection step above (`chain_objpegboards_for_point`, a peg-board-path-table lookup by point id) silently missed some of these points** -- `cavity.wire_position_pegboard`/`terminal.wire_position_pegboard` can return a per-wire clone of a structural stub whose own id never matches the wire's own path-table entry for that stub (see `handlers/rope_pull_handler.md`'s "Part 8" for the full story). Replaced with `chains_bound_to_point`, which inspects each point's own already-bound callbacks directly instead of looking anything up by id. **User-confirmed live: this fixed it.**
