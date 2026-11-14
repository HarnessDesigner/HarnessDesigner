# harness_designer/database/global_db/bases.py

Base classes for the catalog (`global_db`). Unlike `pjt_bases.py` the catalog is not held in memory as a whole: rows are cached one at a time, for as long as their wrapper object lives.

## Line 570-599 (`_cache_row`, `_evict_row`) and 155-182 (`EntryBase.__init__`) — one SELECT per wrapper, then dict lookups
Creating a wrapper (`_EntrySingleton.__call__` -> `EntryBase.__init__`) runs `SELECT <every column> FROM <table> WHERE id=?` and stores `dict(zip(field_names, row))` in `_row_cache`; the dict is dropped when the wrapper is garbage collected. After that `select('col', id=...)` (line 617) returns from the dict. Measured on the real database: a single-row select by id takes about 17-20 us; 200 of them 3.4 ms versus one `IN (200)` query at 1.7 ms. A whole-table `SELECT *` on `housings` takes 553 ms (ids only 31 ms) for 81,093 rows, so a per-wrapper load is the right design for a catalog this size.
Improvement worth considering: a batched preload (`_cache_rows(ids)` using `WHERE id IN (...)`) for places that wrap many rows at once (part search results, `__iter__` consumers), which halves the per-row cost. Memory: the same dict per live wrapper, just filled earlier. The dicts hold the wide columns too (`compat_*` arrays as text, `aabb`/`obb`, `angle3d`/`quat3d`), so a housing row is several KB; that is why eviction on garbage collection matters and why preloading a whole table would be the wrong choice.

## Line 402-459 (`__getitem__`, `__iter__`, `__contains__`) — still SQL
Each runs its own query: `__getitem__` does `SELECT *`, `__iter__` selects every id, `__contains__` selects the id. The table classes put the singleton short-circuit in front (`item in EntryClass or item in self`) so a live wrapper skips the query. `__iter__` on a table with tens of thousands of rows returns 80k ids (31 ms on `housings`) and must not be used inside a loop.

## Line 617-660 (`select`) — non-id selects go to SQL, and the big catalog tables have no FK indexes
A lookup by anything other than a cached id is a real query. On the real database `SELECT id FROM housings WHERE family_id=?` takes 35 ms (81k rows, no index on `family_id`) versus 0.1 ms with an index; `part_number` and `name` are `UNIQUE` and already indexed (0.007 ms). The FK columns used as search filters have no index, except `wire_conductors.wire_id` and `deratings`. See `README.md`, finding 4, for the cost.

## Line 808-909 (`search`) — string-built SQL with joins, per filter change
Builds `SELECT ... FROM <table> tbl1 JOIN ...` plus a `WITH results AS (...) SELECT COUNT(*), *` wrapper and runs it in one statement. Measured on the real database with three joins: 276 ms unfiltered (81k rows), 69 ms with one filter, both dominated by the scan (the `family_id` filter alone is 35 ms of the second). The cost is in the missing indexes and in returning every row when the filter is empty (the dialog should page or limit if it does not). The string building (`repr(item)` per value) is microseconds.

## Line 462-512 (`insert`) — three statements per row
`INSERT` + `commit` + a read-back `SELECT` of every column to fill the row cache. Fine for the one-row inserts the editor does; bulk seeding goes through the builder.

## Line 676-700 (`update`)
`UPDATE` + `commit` + `cached.update(kwargs)`. One commit per write (about 0.015 ms on WAL). There is no batching API on the catalog tables; the catalog is edited by hand, one cell at a time, so none is needed.

## Line 515-567 (`export_as_json`)
Runs one query per exported row inside a loop. Export is a rare action; a single `SELECT *` would be faster but is not worth changing unless export becomes routine.

## Memory
`_row_cache` plus the weak `_instances` registry are bounded by the number of live wrappers. Nothing is held for rows no one is looking at.
