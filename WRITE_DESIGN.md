# Table-store persistence for drag, rotate, insert, and delete

Status: **Phase 1b implemented (section 4.12/5); Phase 1c, 2, and 3 not
started.** Last revised 2026-10-11. Open items are in section 7.

Scope: every project table (`pjt_*`) and every view (3D, schematic, peg board).
Global (`global_db`) rows are covered in section 4.9. The cascading-write
pattern in section 1 is not unique to housings -- it's the same shape on
`PJTTransition` and on the wire-reroute path (section 4.12 lists every
call site).

**2026-10-11 finding: the cache half of this design already exists in the
tree, just not connected to anything.** `database/project_db/table_data.py`
(`TableData`) already implements sections 4.1-4.8 almost exactly as specced:
`load()` (4.2), `change()`/`insert()`/`delete()` (4.3-4.5), the guard flag
(4.5a, as the module constant `RAW_DELETE_IMMEDIATE`), `RowDeletedError`
(4.6, named exactly as section 7b proposed), and the flush half --
`update_statements()`/`insert_statement()`/`delete_statement()`/
`commit_flushed()` (4.8). `PJTTableBase.load_cache()` already calls
`TableData.load()` for every one of the ~26 project tables, once per
project, from `PJTTables.load` (`pjt_bases.py` line 1178) -- so section
4.2's "pull every row" cache is live today, and every read path
(`select`/`__getitem__`/`__iter__`/`__contains__`) already serves from it
(section 4.10 is effectively done).

**What's still missing is only the write side.** `PJTTableBase.update`/
`insert`/`delete`/`batch_update` call `_require_cache()`, but only to keep
the cache in sync after writing straight to the database -- via
`cache.mirror_update`/`mirror_insert`/`mirror_delete`, a different set of
methods from the pending-write ones above. The pending-write/flush API
(`change`/`insert`/`delete`/`update_statements`/`commit_flushed`) has no
caller anywhere in the tree. So every `update()`/`batch_update()` call still
costs a real `UPDATE`/`executemany` + `commit` on every single mouse-move
frame, exactly as section 1 describes -- the cache does not yet suppress
anything. Section 4.12 is the plan to close that gap specifically for move/
rotate gestures (inserts/deletes get the same treatment as a natural side
effect, but aren't the hot path this revision is about).

---

## 1. The problem

Every mouse event during a drag or rotate writes the database. Points and angles
call the database from their callbacks (`pjt_housing.py` `_update_position3d`
line 2082, `_update_angle3d` line 2393, `pjt_point3d.py` `_update_point` lines
289-335), so one event costs a batch write plus one individual `UPDATE` and commit
per terminal point. The 3D drag also re-solves peg-board chains every event
(`rope_pull_handler.realize_3d_move`), which scans the whole bundle and
wire tables each time. Measurements are in section 2.

The same shape repeats on every other cascading owner, not just housing:

- `PJTHousing`: `_update_position3d` (2082), `_update_position_pegboard` (1928),
  `_update_position2d` (2258), `_update_angle3d` (2393), `_update_angle_pegboard`
  (2709), `_update_angle2d` (2945) -- each does its own vectorized numpy delta,
  then one `batch_update()` call into `pjt_points3d`/`pjt_points2d`/
  `pjt_points_pegboard`, per mouse-move frame.
- `PJTTransition`: `_update_position3d` (393), `_update_position_pegboard` (494),
  `_update_angle3d` (567/512), `_update_angle_pegboard` (632/585) -- same pattern,
  one rigid delta applied per branch's own point.
- `wire_routing/reroute.py` `apply_shifts` (line 255) -- the wire/bundle
  equivalent: moves every waypoint a reroute touches with one `batch_update`
  into `pjt_points2d`. Called from two places, both per-frame: directly from a
  wire's own schematic drag (`drag_handlers/editor_schematic/wire.py` line 672,
  `Wire.__call__`), and from `follow_moved` (reroute.py line 359), which a
  housing's own move drag calls on every one of ITS frames so the wires
  attached to it follow along -- i.e. a housing drag that owns wires can nest
  an `apply_shifts` batch_update inside its own per-frame `_update_position3d`
  batch_update today. Whatever gesture mechanism housing/transition get must
  nest around this call too (see section 4.12).

All of the above share the same suppression hack: a class- or instance-level
`_skip_db_write` flag (`pjt_point3d.py`, `pjt_point2d.py`,
`pjt_point_pegboard.py`, `mixins/angle3d.py`, `mixins/angle_pegboard.py`) set
`True` for the duration of the per-point assignment loop that follows the
`batch_update()` call, purely so each point's own ordinary `_update_point`/
`_update_angle3d` callback doesn't ALSO fire a redundant single-row `UPDATE`
for a row the batch call just wrote. Render/propagation callbacks are kept
alive by an explicit `_process_callbacks()` call outside the suppressed
block. Section 4.12 retires this whole mechanism -- once a gesture is open,
there is no "redundant write" to suppress, because the per-point assignment
IS the only write that happens (as a cache dict update), and the explicit
`batch_update()` call goes away entirely.

Every project-table write goes through `PJTTableBase` (`pjt_bases.py`: `update`
line 685, `batch_update` line 708, `insert` 574, `delete` 671, `execute` 885,
`commit` 917). That is the choke point for the new design.

## 2. Measurements (local SQLite, WAL)

Scratch benchmarks, not in the repo. Local-disk numbers only. MySQL is not measured
and is not active in the current code.

| Measurement (per mouse event) | Time |
|---|---|
| One-row `UPDATE` plus `commit` | ~0.015 ms |
| 200 individual `UPDATE` + `commit` (terminal-point pattern) | ~3.7 ms |
| Same 200 rows as one `executemany` + `commit` | ~0.35 ms |
| 600 rows: Python row-building only | ~0.86 ms |
| 600 rows: row-building + `executemany` + `commit` | ~1.9 ms |
| 2,500 rows: row-building + `executemany` + `commit` | ~8.0 ms |

A commit is nearly free under WAL. Statement count and per-row Python work are the
levers. The rope-pull path and the cascade's own Python cost are not measured yet.
The baseline comes from the timing tool (section 5, Phase 0).

## 3. What already exists

- `rope_pull/offline_store.py` and `handlers/rope_pull_handler.py` already hold a
  mid-gesture in-memory overlay for peg-board chain drags. It is the same idea,
  applied to one topology. Phase 3 folds it into the new store.
- `drag_handlers/editor_3d/generic.py` `Generic.__init__` and `delete()` already
  bracket a gesture for the wire service loop. The gesture hooks go here.
- `debug.py` is rewritten (2026-10-06) for timing: `begin_capture()` and
  `end_capture()`, with inclusive and self time per call. Phase 0 uses it.
- `Config.debug.database.profile_queries` with `dump_query_profile()` already counts
  SQL statements per normalized query. Phase 0 uses it for statement counts.
- `id_generator.py` generates project row ids. On SQLite the id is built locally
  from a process-wide monotonic clock. On MySQL it is a server call
  (`next_project_row_id`, which holds a lock and takes the user from
  `CURRENT_USER()`). The server call is what keeps MySQL ids unique across users.

## 4. The design

### 4.1 Layers

- **Table store.** Each project table instance holds a raw-data dict: row id to the
  row's column values. The store is the current state of the project's rows, and
  reads come from it.
- **Singleton cache.** Unchanged. It controls which live Python object represents a
  row. It holds no row data, and it does not decide what is stored.
- **Pending storage**, held by each table, all keyed by row id:
  - `inserts`: ids of rows created but not yet written.
  - `updates`: row id to the set of columns changed since the last write.
  - `deletes`: ids of rows whose delete is waiting for the database.

### 4.2 Load

- One query per project table per project, selecting every column for that
  project's rows. The results fill the raw-data dict.
- Loading is not object creation. The table pulls and holds the data. Python objects
  are still created on demand through the singleton cache. The load order that
  matters (cavities before housings, MEMORY.md 2026-09-04) applies to object
  construction, not to the data load.

### 4.3 Changes

- A row reports a change with the table: `table.change(row_id, column, value)`.
- The table writes the value into the raw-data dict and adds the column to the
  row's entry in `updates`. This is a dict write, so there is no SQL on the event
  path.
- If the row id is in `inserts`, the change only updates the raw data. The pending
  insert already reads the raw data when it is written, so it carries the change.
- If the row id is in `deletes`, the change is ignored.
- A row's dirty state is the table's business. The row object has no dirty flag and
  holds no pending write, so a garbage-collected object loses nothing.

### 4.4 Insert

- `insert` generates the id with the existing mechanism (SQLite: local clock, MySQL:
  one server call per insert). It creates the row in the raw-data dict and adds the
  id to `inserts`. Nothing else is held, and nothing is written.
- Insert ids are generated when the row is created. That is the one point where a
  MySQL round trip happens, and it is the same point where it happens today.
- Inserts are never buffered as values. The flush reads each pending insert's row
  from the raw-data dict when it writes.

### 4.5 Delete

- The row's own `delete()` decides which child rows go, as it does today. It must
  read anything it needs from the store **before** it marks the row deleted, because
  a read after that raises (section 4.6).
- `table.mark_deleted(row_id)`:
  1. If the id is in `inserts`: remove it from `inserts` and remove its raw data. The
     row never reached the database, so nothing else happens. This is the cancel case.
  2. Otherwise: remove the id from `updates`, add it to `deletes`.
  3. The raw data is then handled by a guard (section 4.5a).
- Object cleanup (`remove_object`, reconnects, the singleton entry) is unchanged.

#### 4.5a The guard: when raw data is removed for a delete

Two paths, selected by one flag. Both are written, so either can be used to check
the other.

- **Immediate (`RAW_DELETE_IMMEDIATE = True`).** The raw data is removed as soon as
  `mark_deleted` runs. Reads of the id raise from that point on. The reference check
  sees the row as gone, with no subtraction step.
- **Deferred (`RAW_DELETE_IMMEDIATE = False`).** The raw data stays until the delete
  commits. Reads still succeed during the gesture. Updates to the id are ignored. The
  reference check subtracts the delete storage.

The flag is one module-level setting, read by `mark_deleted`. Switching it changes
nothing else.

### 4.6 Reads and updates on a deleted row

- Getters read the raw-data dict. A row id that is not there raises a custom
  exception. The name is `RowDeletedError` (subclasses `Exception`, not `KeyError`, so
  an existing `except KeyError` cannot hide it). This applies on both delete paths
  once the raw data is gone.
- A `change` on a deleted id is ignored in the deferred path, and raises in the
  immediate path, since there is no row to change.

### 4.7 Reference check

- The project gathers referencing rows for a candidate point from each table's raw
  data, in memory. Pending inserts are part of the raw data, so they count.
- Immediate path: deleted rows are already gone, so the result is the answer.
- Deferred path: each table subtracts its `deletes` set from the result.
- `PJTPoint*.is_referenced` and `_find_unreferenced_point_ids` both use this.
- No cache.

### 4.8 The flush

Called from the project instance held by the mainframe. One transaction:

1. **Deletes**, per table, `DELETE ... WHERE id IN (...)`. Referencing tables come
   before the tables they reference, so MySQL's enforced foreign keys are satisfied.
2. **Inserts**, per table, in table order (parents before children). Each row is read
   from the raw-data dict, and inserts are grouped by table. One `executemany` per
   table.
3. **Updates**, per table. Rows are grouped by their set of changed columns. Each
   group is one `UPDATE ... SET col = ?, ... WHERE id = ?` and one `executemany`. The
   values come from the raw-data dict at flush time, so the last value wins.
4. **Commit.**
5. **After the commit succeeds:** clear `inserts`, `updates`, and `deletes`, and, on
   the deferred path, remove the deleted rows' raw data.

If any step raises, nothing is cleared. The next flush retries the same work. This
makes a failed flush recoverable without any silent fallback.

Nested gestures use a depth counter. Only the outermost flushes. A gesture is a
`with` block, so `__exit__` runs on an exception too.

### 4.9 Global rows

- Global (`global_db`) tables are not bulk-loaded -- a catalog table can be far
  bigger than anything project-scoped, so there is no per-table equivalent of
  section 4.2's load. Instead the cache is per-row, on `TableBase._row_cache`
  (`db_id -> {column: value}`), and keyed to the row's own lifetime rather than
  the table's: `EntryBase.__init__` -- the one and only construction of a row's
  wrapper, since every row is an `_EntrySingleton` -- loads that one row in with
  a single query, and `_EntrySingleton`'s existing weakref cleanup (already
  there to drop the singleton registry entry once nothing references the
  wrapper) evicts the row from `_row_cache` at the same moment. A row with no
  live wrapper is simply not cached; the next thing that constructs one loads
  it again.
- `TableBase.select()` serves a plain `id` lookup (the shape every column
  mixin's lazy property getter uses, e.g. `self._table.select('rgb',
  id=self._db_id)`) from `_row_cache` when that row is already cached. Any
  other shape -- a different column, a compound `WHERE`, or an id that was
  never cached -- still queries the database, same as before.
- Global writes are user-driven and rare. `update()`/`delete()` still run their
  own statement immediately, and now also mirror into `_row_cache` (updating it,
  or evicting the row) when that row happens to be cached. `insert()` reads the
  new row back (kwargs can omit a column the database defaults) and seeds
  `_row_cache` with it, so the entry wrapper every `insert()` override
  constructs right after (e.g. `ColorsTable.insert`) finds it already cached.
  The pending/deferred-flush storage in sections 4.3-4.8 is project-only; global
  tables have no flush, nothing ever queues.
- Global rows are small. Their large-looking columns (`cads.data`,
  `datasheets.data`, `images.data`) are unused and default to `NULL`. Files are on
  disk, and the path is built at runtime from settings and the file's uuid.

### 4.10 Selects

- **Already done, as of the 2026-10-11 finding in the header.** `PJTTableBase.select`/
  `__getitem__`/`__iter__`/`__contains__` already branch on `__uses_uuid_id__` and
  read from `_require_cache()` (`TableData.select`/`row`/`row_ids`/`contains`)
  instead of the database, for every migrated project table. `TableData.select`
  itself already returns a row the instant `change()` updates it (`change` does
  `row.update(values)` on the same dict `select` reads), so once section 4.12's
  writes route through `change()` too, a read mid-gesture sees the in-flight
  value with no extra work.
- What's NOT yet true: the 577-call-site count below refers to raw `self._con`/
  `self._table.db...execute` call sites that bypass `PJTTableBase.select` entirely
  (section 4.11/7a) -- those still hit the database regardless of cache state, and
  still need the per-case review that section describes.
- Single-row lookups by id are already dict reads (`__getitem__`). Lookups by a
  foreign-key column still fall back to a scan over `TableData._rows.values()`
  inside `select()` -- fine for the sizes involved (section 7h), revisit only if
  a profiled call site shows otherwise.

### 4.11 Choke point

- Before Phase 1, confirm nothing writes through `self._con` outside `pjt_bases.py`
  (step 0 in section 5). Each hit gets evaluated for what it actually does. Any write
  path that bypasses the store has to be routed through it.

### 4.12 Gestures: no database writes while a move or rotate is active

This is the part of Phase 1 that directly answers "stop writing to the database
during a drag/rotate, write once when it ends." It doesn't need the full
Phase 1 (every table, every call site) to land first -- it only needs the
write side of `PJTTableBase` wired to the pending-write half of `TableData`
that section header's finding says already exists. Scope is every cascading
owner listed in section 1: `PJTHousing`, `PJTTransition`, and
`wire_routing.reroute.apply_shifts`.

**The gesture.** A project-level depth counter (mirrors section 4.8's "nested
gestures" rule, which already anticipates this):

```
project.begin_gesture()   # depth 0 -> 1: opens the gesture
...                       # depth already > 0: just increments
project.end_gesture()     # depth 1 -> 0: flushes every dirty table, then clears
```

`begin_gesture`/`end_gesture` is a `with project.gesture():` block in practice,
so an exception during the gesture still decrements and still flushes whatever
was accumulated before the exception, same as section 4.8's `__exit__`
guarantee. Only the outermost call flushes -- this is what makes
`follow_moved`'s nested `apply_shifts` call (section 1) free: it opens its own
gesture, sees depth already > 0, and does nothing on exit except decrement.

**Where it opens and closes.** Every entry point in section 1 that currently
brackets a drag or rotate already has an exact begin/end pair to hook:

- Move (`drag_handlers/base.py` `DragHandlerBase`): construction is the
  existing begin-of-drag moment (`Generic.__init__`, `drag_handlers/
  editor_3d/generic.py` line 69, covers housing/transition/splice/
  wire_service_loop/bundle_layout/wire_layout moves); `delete()` (line 82) is
  the existing end-of-drag moment, called exactly once on both commit and
  abort already -- open the gesture in `__init__`, close it in `delete()`.
- Rotate (`rotation_handlers/rotation_ring/inner_ring.py`): `begin_drag`
  (line 137) / `end_drag` (line 216). Confirmed this is the right granularity
  by checking all three callers (`rotation_handlers/editor_3d/generic.py`
  lines 419/437, `editor_schematic/generic.py` 404/421, `editor_pegboard/
  generic.py` 316/333) -- each pair brackets exactly one axis-handle grab,
  which is exactly one rotation action; switching handles between grabs
  already closes one gesture and opens the next, with no motion (hence no
  writes) in between, so no cross-ring coordination is needed.
- Wire/bundle waypoint drag (`drag_handlers/editor_schematic/wire.py`
  `Wire.__call__`, line 672's `apply_shifts` caller): same construct/delete
  bracket as the move case above.

**What changes in `PJTTableBase`.** `update`, `insert`, `delete`, and
`batch_update` (`pjt_bases.py` lines 741/613/722/769) each gain one branch:
when `self.db.project.gesture_depth > 0` (or equivalent), call the matching
pending-write method on the already-loaded cache (`cache.change(db_id,
**kwargs)` for `update`, one `cache.change()` per row for `batch_update`,
`cache.insert`/`cache.delete` for the other two) and return -- no `self._con`
call, no commit. Depth 0 keeps today's behavior exactly (`self._con.execute`
+ `mirror_update`/etc.), so nothing outside a gesture changes at all.

**What the flush does.** On the outermost `end_gesture`, iterate every loaded
table (`PJTTables`' fixed list, `pjt_bases.py` line ~1166) and, for each one
whose cache has pending state, pull `update_statements()`/`insert_statement()`/
`delete_statement()`, run them, commit once for the whole project (not once
per table), then call `commit_flushed()` on every table touched. This is
already the exact shape section 4.8 specs; the only new work is the loop that
finds which tables are dirty (a cheap check: `bool(cache._updates or
cache._inserts or cache._deletes)`, or `TableData` grows a one-line
`is_dirty` property to avoid reaching into its internals from outside).

**What this retires, once it's in place.** Every explicit `batch_update()`
call in section 1's list, and every `_skip_db_write` flag site named there.
The vector math in e.g. `_update_position3d` is unchanged -- numpy delta,
one array add -- but instead of then calling `batch_update()` and toggling
`_skip_db_write` around a suppressed assignment loop, it just assigns
`pos.x`/`pos.y`/`pos.z` on every point directly. Each assignment still runs
the point's own ordinary `_update_point`/`_update_angle3d` callback, but
that callback's `table.update(...)` call is now a dict write (because the
gesture is open), not SQL -- so there is no redundant write left to
suppress, and the suppression machinery has nothing to do. This is the
"vector math now, set values, no DB write happens on that path" behavior
asked for -- it falls out of routing the existing per-point write through
the existing (currently-bypassed) cache, not from adding a new batching
layer alongside it.

**Why the flush is still "a small number of updates" and not one-row-at-a-
time.** `TableData._updates` is keyed by row id; a point touched on every one
of a drag's 200 frames still only has one entry, overwritten each frame, so
`update_statements()` groups the WHOLE gesture's accumulated changes by
changed-column-set and emits one `executemany` per table per column-set --
for a pure position drag, that's one `executemany` into `pjt_points3d` (or
`pjt_points2d`/`pjt_points_pegboard`) covering every point the gesture ever
touched, no matter how many frames or how many cascading owners contributed
to it in a nested gesture.

**What does NOT change in this pass.** `rope_pull/offline_store.py`'s
in-memory overlay (peg-board chain topology during a drag -- waypoints
appearing/disappearing, not just coordinates) stays its own bespoke
mechanism; WRITE_DESIGN.md Phase 3 already defers folding it into the store,
and nothing here forces that fold early. `realize_3d_move`'s per-event
full-table scan (section 1, Phase 2) is also untouched -- this section is
about removing DB writes during the gesture, not about the Python cost of
the cascade itself.

**New open items this raises** (added to section 7):

- **Nested gesture + reroute -- resolved, 2026-10-11.** `apply_shifts` itself
  opens no gesture of its own; it relies on one already being open. Checked
  both callers: the schematic `Wire` drag handler opens one in its own
  `__init__`, and `follow_moved` only ever runs from inside the schematic
  move `Generic`'s own per-frame callback, whose `__init__` also opens one
  -- so by the time `apply_shifts` runs, either path, a gesture is always
  already open. Nothing to add; `apply_shifts` deliberately stays as a
  plain function with no gesture logic of its own.
- **Crash safety, now higher-stakes.** Section 7e already flagged that a
  crash mid-gesture loses unflushed work; a multi-second rotate that
  previously wrote the database every frame now writes nothing until
  release, so a crash loses the whole gesture instead of losing nothing.
  Still unresolved -- same open question, bigger blast radius.

## 5. Phasing

### Phase 0: baseline (no code change)

- Use `begin_capture()` / `end_capture()` (section 3) on one real drag and one
  rotate. Set `log_duration` on and `log_args` off, then restart.
- Use `dump_query_profile()` for statement counts per event.
- **The user runs the app and reports the output.** The assistant does not launch the
  GUI.

### Phase 1: the table store

**Already done** (2026-10-11 finding, see the header and section 4.10):

1. ~~Add the raw-data dict, the three pending storages, `change`, `insert`,
   `mark_deleted`/`delete`, the guard flag, `RowDeletedError`, and the flush.~~
   -- `table_data.py`'s `TableData` already has all of this.
2. ~~Load each project table once, per project.~~ -- `PJTTableBase.load_cache()`,
   called for every table from `PJTTables.load`.
3. ~~Convert the `select` call sites.~~ -- `select`/`__getitem__`/`__iter__`/
   `__contains__` already read the cache for every `__uses_uuid_id__` table.

**Still to do**, split into two slices that don't have to land together --
1b is the narrow slice that answers this round's actual question (stop
writing during move/rotate); 1c is the rest of the original Phase 1 scope
(every other write path, not just the cascading-move ones):

**Phase 1b -- gesture-scoped writes (section 4.12).** This is the direct,
minimal path to "no database writes while a move or rotate is active."
It touches one choke point (`PJTTableBase.update`/`insert`/`delete`/
`batch_update`) and the handful of begin/end pairs section 4.12 names --
nothing else needs to change first.

**Done, 2026-10-11:**

1. ~~Choke-point check (section 4.11)~~ -- confirmed: every cascading owner
   (housing, transition, reroute) already wrote exclusively through
   `PJTTableBase.update`/`batch_update`; nothing bypassed it.
2. ~~Add the gesture depth counter to `Project`~~ -- added to `PJTTables`
   (`gesture_depth`/`begin_gesture`/`end_gesture`/`gesture()`, the last a
   `_GestureContext` for `with project.gesture():`), with a thin delegating
   `begin_gesture`/`end_gesture`/`gesture` on `objects/project.py`'s
   `Project` (what `mainframe.project` actually returns -- its `.ptables` IS
   the `PJTTables` instance).
3. ~~Branch `update`/`batch_update` on gesture depth~~ -- done, per section
   4.12 exactly (`insert`/`delete` stay immediate always for now -- see
   4.12's note on why that's a deliberate, separate cut from this round).
4. ~~Add the flush-on-outermost-`end_gesture` loop~~ -- `PJTTables.
   _flush_gesture`, visiting tables via a new `_ordered_project_tables()`
   (the same parent-before-child list `load()` already used, now shared).
5. ~~Open/close the gesture at the begin/end pairs~~ -- all six: the three
   move `Generic.__init__`/`delete()` (3D/schematic/pegboard) plus the
   schematic `Wire.__init__`/`delete()`, and the three rotation
   `begin_inner_drag`/`end_inner_drag` (3D/schematic/pegboard). Every
   `end_gesture()` call is in a `finally` (a gesture that never closes would
   silently defer every later write app-wide), and every `begin_gesture()`
   is placed so it can't run without the matching close later firing either
   (the rotation ones specifically go *before* `ring.inner.begin_drag()`,
   not after -- `end_inner_drag`'s firing depends on `is_dragging`, which
   `begin_drag()` sets on its very first line, not on `begin_inner_drag`
   itself returning normally). Found and fixed in passing: `Rings3D`/
   `Rings2D`/`RingsPegboard` never actually stored the `mainframe` they
   were constructed with, as a real attribute to resolve against, even
   though `Rings2D.detach()` already called `self.mainframe.project` --
   a pre-existing latent `AttributeError` this work needed to not inherit.
6. ~~Retire the explicit `batch_update()` calls and every `_skip_db_write`
   site~~ -- all of them, across `pjt_housing.py` (6 cascades),
   `pjt_transition.py` (4), `wire_routing/reroute.py`'s `apply_shifts`, and
   the now-dead flag/check in `pjt_point3d.py`/`pjt_point2d.py`/
   `pjt_point_pegboard.py`/`mixins/angle3d.py`/`mixins/angle_pegboard.py`.
   The angle-result `batch_update()` calls for cavity/terminal/seal/
   accessory `quat3d`/`angle3d` rows (further down `_update_angle3d`/
   `_update_angle_pegboard`) were deliberately left alone -- they already
   benefit from step 3's generic `batch_update` branch with no code change,
   and (discovered while reading them) have no per-object callback fallback
   to redirect to anyway: `Angle`'s own `__exit__` (`CallbackMixin`) never
   auto-fires callbacks, and nothing in those loops calls
   `_process_callbacks()` -- the explicit batch write is the ONLY thing
   that ever persisted them, before and after this change.

**Acceptance for 1b:** zero SQL statements per mouse event during a drag and
a rotate; one transaction per gesture, covering every table any cascading
owner touched (including a nested `apply_shifts`) -- verified by direct
code reading of every touched call site (listed above) plus a standalone
script exercising the real `TableData` class (not a reimplementation)
against a temporary in-memory SQLite table, confirming: a point touched on
every one of 50 simulated drag frames produces exactly one `UPDATE`
covering its final value, not an intermediate one; a mid-gesture read sees
the in-flight value; the real database table is untouched until the flush
runs. **Not verified by running the app** -- this container has no PySide6
(confirmed: `import harness_designer...` fails at the package's own
`__init__.py` before reaching any file this change touches), consistent
with Phase 0's own note that the assistant doesn't launch the GUI. The user
running a real drag and rotate in the app, plus a flush test against a real
on-disk project database, is still the outstanding verification step.

**Phase 1c -- the rest of the original Phase 1 scope.**

1. Project-level reference check (section 4.7).
2. Route every remaining `PJTTableBase` write path through the store outside
   a gesture too, where it isn't already (most already are, via Phase 1b's
   step 3 -- this is cleanup of anything that still writes through
   `self._con` directly per section 4.11/7a).

**Acceptance for 1c:** the original Phase 1 acceptance criterion -- zero SQL
statements per mouse event, full write-side parity with the read side.

### Phase 2: the rope-pull path

- Replace the per-event full-table scans in `realize_3d_move` with lookups that use
  the store.

### Phase 3: fold in the existing overlay

- Make `offline_store` and `_commit_overlay` use the store, so there is one
  persistence path. A cleanup, not a speed change.

## 6. Expected gains

- **Local SQLite:** the database share of each event drops to zero during a gesture,
  with one transaction at release. The total gain depends on the rope-pull and
  cascade Python costs, which Phase 0 measures.
- **MySQL:** each individual statement was a network round trip. Removing the
  per-point pattern is where the large gain would show. Not measurable here, since the
  MySQL path is not active.

## 7. Open items

a. **Guard default.** ~~Which delete path to run by default (section 4.5a).~~
   Already decided in the tree: `table_data.py`'s `RAW_DELETE_IMMEDIATE = True`
   module constant picks the immediate path. Revisit only if testing surfaces a
   reason to flip it.
b. **Exception name.** ~~`RowDeletedError` is proposed.~~ Already the name used
   in `table_data.py`.
c. **Unconverted selects.** Any select missed during conversion returns database
   state during a gesture. Is a flush-before-select acceptable as a safety net for
   the ones left unconverted, or should every call site be converted first?
d. **Foreign-key defaults.** Most foreign keys omit `on_delete`, so the DDL emits
   `ON DELETE SET DEFAULT`. The code documents `NO ACTION`. On MySQL this would make
   the engine reassign child rows to the NIL-id default. Confirm the intent, and
   whether to change the default on both connectors.
e. **Crash safety.** A process crash loses the store's pending work. Accept that, or
   add a periodic flush during long gestures?
f. **Other readers.** Does any other process read project rows during a gesture?
   `process/db_broker.py` opens the same SQLite file.
g. **Undo.** Is there an undo system that depends on per-event writes? None was found
   in the paths read.
h. **Memory.** The store holds every project row. The current belief is that the
   project tables are small (mostly ids, floats, and integers), but the size is not
   measured on a large project.
i. **MySQL.** The MySQL path is not active, so the design is untested there. The
   current belief is that the same id mechanism works unchanged.

## 7a. Deferred: raw `execute` and `executemany` call sites

Not started. These need a per-case review before Phase 1 touches them. The `select`
sites are classified in section 4.10; these are the direct SQL calls that bypass the
table layer.

- `database/project_db/pjt_housing.py`: `executemany` in `PJTHousingsTable.insert`
  (lines 397, 406, 415, 427) and `PJTHousing.update_cavities` (lines 665, 674, 683,
  700). They write points and cavities directly.
- `database/project_db/pjt_housing.py`: `cache_names` (line 1066), a three-table
  `LEFT JOIN` over cavities, 2D points, and terminals. Needs an in-memory join.
- `database/project_db/pjt_housing.py`: `_find_child_points` and
  `_find_child_points_pegboard` (lines 1870, 1906). They run on every housing drag
  frame -- called directly from inside `_update_position3d`/`_update_angle3d`
  (lines 2147/2471) and `_update_position_pegboard`/`_update_angle_pegboard`
  (lines 2006/2800). This means section 4.12's gesture work removes the WRITE
  cost from every drag frame but not this READ cost -- these two stay a raw
  query per frame until they're converted too. Not a blocker for 4.12 (reads
  were never the thing being suppressed), just a residual cost worth knowing
  about going in.
- `handlers/transition_handler.py`: raw writes in `_repoint_all_references` (line 97)
  and `_delete_point_if_orphaned` (lines 114, 121).
- `database/project_db/pjt_circuit.py`: string-built SQL in `PJTCircuitControl`
  (lines 981, 1039, 1048). Includes a `max(circuit_num)` aggregate.
- `database/project_db/mixins/color.py`: lines 119 and 138 are project-side
  object-editor calls. Line 155 is a global colors insert and stays as it is.
- `database/project_db/cleanup.py`: raw reads and deletes (lines 157, 167, 216).
- `handlers/seal_handler.py` (line 50) and
  `ui/pegboard_table/wire_table.py` (lines 1046, 1048): raw project reads.

The `execute` calls for global tables (catalog editor, global controls, resources,
config, process) are out of scope and stay as they are.

## 8. Decision log

- 2026-10-06: discovery and plan. Measurements on local SQLite WAL.
- 2026-10-06: revised to the table store. Rows report changes to their table. Inserts
  go to the store with only the id held in pending storage. Deletes cancel pending
  inserts and updates, and their raw-data removal is selected by a guard flag. Global
  rows are fetched whole on first access and written immediately. The reference check
  runs in memory. The flush clears pending state only after commit succeeds.
- 2026-10-11: investigated the request to stop writing to the database while a
  housing move/rotate is active (then generalized to every cascading owner:
  transition, and wire/bundle reroute). Found that `TableData` (sections
  4.1-4.8) and project-table cache loading (4.2) already exist in the tree,
  unused on the write side -- only `PJTTableBase`'s write methods and the
  gesture concept itself are missing. Added section 4.12 (the gesture
  mechanism) and split Phase 1 into 1b (gesture-scoped writes -- the direct
  answer to this round's question) and 1c (the rest of the original scope).
  Corrected 4.10: selects already read the cache, that part of Phase 1 is
  done, not pending. Closed open items (a) and (b) -- both already decided in
  the existing code.
- 2026-10-11 (later the same day): implemented Phase 1b. Gesture depth
  counter on `PJTTables` (`begin_gesture`/`end_gesture`/`gesture()`), a
  gesture-aware branch in `PJTTableBase.update`/`batch_update`, the flush
  loop, and the six begin/end hook pairs (move x3, rotate x3). Retired every
  explicit cascade `batch_update()` call and `_skip_db_write` site in
  `pjt_housing.py`/`pjt_transition.py`/`wire_routing/reroute.py` and the
  point/angle classes that flag lived on. Left the cavity/terminal/seal/
  accessory angle-result `batch_update()` calls alone (already gesture-aware
  for free, and have no per-object callback fallback to redirect to -- see
  item 6 above). Verified with `ast.parse`/`pyflakes` on every touched file
  (zero new warnings against the pre-change baseline) and a standalone
  script exercising the real `TableData` against a temporary SQLite table;
  could not run the app itself (no PySide6 in this container). Fixed one
  pre-existing latent bug found along the way: `Rings3D`/`Rings2D`/
  `RingsPegboard` never stored their own `mainframe` reference despite
  `Rings2D.detach()` already depending on it.
