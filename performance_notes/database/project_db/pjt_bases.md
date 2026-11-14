# harness_designer/database/project_db/pjt_bases.py

Base classes for every `pjt_*` table: `PJTTableBase` (the cache-backed table), `PJTEntryBase` (the row wrapper) and `PJTTables` (the registry, the gesture control and the load order). Background in [table_data.md](table_data.md) and `WRITE_DESIGN.md`.

## Line 505-517 (`load_cache`), 1371-1438 (`PJTTables.load`) — one query per table at project load
Each `pjt_*` table with UUID ids loads its rows with a single `SELECT <all columns> ... WHERE id >= ? AND id <= ?` (id range = the project), so a project open costs one query per table (about 40) instead of one per row. That is the right shape; the memory cost is the dict per row (see table_data.md).

## Line 623-697 (`__getitem__`, `__iter__`, `__contains__`) — in-memory for UUID tables
All three answer from `TableData` (`row`, `row_ids`, `contains`), with SQL kept only for `ProjectsTable` (non-UUID ids). `__iter__` is `yield from row_ids()`, which lists the ids of every row on each call, so iterating a table inside a loop that runs per frame is O(rows) per call.

## Line 700-768 (`insert`) — gesture inserts are deferred; outside a gesture the insert reads the row back
Inside a gesture the row goes to the cache only. Outside a gesture it does `INSERT` + `commit` + a read-back `SELECT` of every column (to pick up defaults) + `mirror_insert`: three statements per row. `WRITE_DESIGN.md` says no caller relies on a schema default any more (checked 2026-10-13), so the read-back could be dropped for tables whose callers supply every column; that removes one query per insert. Low priority: inserts are click-triggered, and the bulk case (a new housing's cavity set) uses `executemany` directly.

## Line 771-826 (`select`) — SQL path only for non-UUID tables; UUID tables go to `TableData.select`
Fine. The `OR` costs and the index behaviour are in table_data.md.

## Line 829-921 (`delete`, `update`, `batch_update`) — gesture-aware
Outside a gesture each `update` is `UPDATE` + `commit` + a cache mirror (about 0.015 ms on WAL, per the `WRITE_DESIGN.md` measurements); `batch_update` is one `executemany` + one commit and mirrors each row. Inside a gesture they only touch the cache. Every drag and rotation handler should therefore run inside `begin_gesture()`; a handler that does not pays one commit per row write.

## Line 924-997 (`batch_insert`), 1050-1144 (`_find_unreferenced_point_ids`) — SQL, used by cleanup
`_find_unreferenced_point_ids` builds a CTE with one `(?)` per candidate and a `UNION` of one `SELECT` per matching column, run against the database (not the cache) for every table in the chain by `project_db/cleanup.py`. It runs in chunks (`ProjectCleanup.process_chunk`), not per frame. Because it reads the database, rows changed inside an open gesture are not visible to it, and a large candidate set makes a large parameter list (SQLite's variable limit is 32,766 per statement on a current build). Not a speed problem.

## Line 1553-1598 (`_flush_gesture`)
Deletes, then inserts, then updates in dependency order, each as `executemany`, then one `commit`; only dirty tables are touched. This is the efficient shape and is what makes a drag cost one transaction.

## Line 1359-1368 (`PJTTables.tables`)
Builds the table list by reflecting over `dir(self)` with `getattr` on each access (a loop plus a sort). It is used by the load and shutdown paths, not per frame.
