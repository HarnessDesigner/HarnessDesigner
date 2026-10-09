# Table-store persistence for drag, rotate, insert, and delete

Status: **design settled in discussion, Phase 1 not started.** Last revised 2026-10-06.
Open items are in section 7.

Scope: every project table (`pjt_*`) and every view (3D, schematic, peg board).
Global (`global_db`) rows are covered in section 4.9.

---

## 1. The problem

Every mouse event during a drag or rotate writes the database. Points and angles
call the database from their callbacks (`pjt_housing.py` `_update_position3d`
line 2011, `_update_angle3d` line 2322, `pjt_point3d.py` `_update_point` lines
330-336), so one event costs a batch write plus one individual `UPDATE` and commit
per terminal point. The 3D drag also re-solves peg-board chains every event
(`rope_pull_handler.realize_3d_move`, line 1396), which scans the whole bundle and
wire tables each time. Measurements are in section 2.

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

- The codebase has 577 `select` call sites. Any `select` that reads a project table
  while changes are pending would see database state, not the store, and get a wrong
  answer.
- Every project-table `select` is converted to read the store, or the flush runs
  before it. Conversion is the plan. The specific converted call sites are listed
  during Phase 1, from the call-site scan.
- Single-row lookups by id become dict reads. Lookups by a foreign-key column need an
  in-memory index on that column, or a scan, chosen per call site.

### 4.11 Choke point

- Before Phase 1, confirm nothing writes through `self._con` outside `pjt_bases.py`
  (step 0 in section 5). Each hit gets evaluated for what it actually does. Any write
  path that bypasses the store has to be routed through it.

## 5. Phasing

### Phase 0: baseline (no code change)

- Use `begin_capture()` / `end_capture()` (section 3) on one real drag and one
  rotate. Set `log_duration` on and `log_args` off, then restart.
- Use `dump_query_profile()` for statement counts per event.
- **The user runs the app and reports the output.** The assistant does not launch the
  GUI.

### Phase 1: the table store

1. Choke-point check (section 4.11).
2. Add the raw-data dict, the three pending storages, `change`, `insert`,
   `mark_deleted`, the guard flag, `RowDeletedError`, and the flush.
3. Route `PJTTableBase` writes through the store.
4. Load each project table once, per project.
5. Convert the `select` call sites (section 4.10).
6. Project-level reference check (section 4.7).
7. Gestures in the drag and rotation handlers (`drag_handlers/base.py`,
   `rotation_handlers/rotation_ring/inner_ring.py`, `begin_drag` line 137, `end_drag`
   line 216).
8. Retire `_skip_db_write` and the skip-set logic in `_update_position3d` and
   `_update_angle3d`.

**Acceptance:** zero SQL statements per mouse event during a drag and a rotate; one
transaction per gesture; a headless test of the flush against a temporary project
database, with the store's contents after the flush matching the database row for
row. Run it with `USERPROFILE`/`HOME` sandboxed, one process at a time.

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

a. **Guard default.** Which delete path to run by default (section 4.5a). Both are
   written, so this is decided by testing.
b. **Exception name.** `RowDeletedError` is proposed. Confirm the name.
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
  `_find_child_points_pegboard` (lines 1828, 1850). They run on every housing drag
  frame.
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
