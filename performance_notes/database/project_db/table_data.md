# harness_designer/database/project_db/table_data.py

The in-memory store behind every `pjt_*` table (`PJTTableBase.load_cache`). One `TableData` per table: `_rows` (id -> dict of column -> value), `_order` (insertion order, so index hits come back in scan order), lazily built `_indexes` (column -> value -> set of ids), and the pending `_inserts`, `_updates`, `_deletes` that a gesture flushes in one transaction. The design is `WRITE_DESIGN.md`; this note is only about cost. Measured 2026-11-13 on a synthetic table of 50,000 rows x 20 columns, interpreted Python 3.11:

| Operation | Time |
|---|---|
| `select('x', id=...)` | 0.9 us |
| `select` on an indexed column | 1.2 us |
| first `select` on a new column (builds the index) | about 14 ms at 50,000 rows |
| `select` with `OR=True` | 20.6 ms (a full scan, 0.4 us per row) |

## Memory: a dict per row (the main cost of the design)
`load` (line 135) turns every row into `dict(zip(field_names, row))`. Measured 601 bytes per 20-column row for the dicts and bookkeeping (30 MB for 50,000 rows), plus the value objects (a float is 24 bytes, a 16-byte id 49 bytes, about 25-50 bytes per cell), so roughly 1.1-1.6 KB per 20-column row, or 11-16 MB per 10,000 rows. The real project in the database copy has a few hundred rows per table, so this is small today; it matters only for a project with tens of thousands of rows. The store is a deliberate memory-for-speed trade (every property read is a dict lookup instead of a query), and it keeps `_rows` and every built index alive for as long as the project is open.
Ways to cut it if a large project shows memory pressure, with the price of each: (1) tuples plus one shared column -> position dict per table: about 3x less container memory (not the values), every `row[field]` becomes `row[pos[field]]`, and every `_row_matches`/`_store`/`_revalue` path changes; (2) drop the `_order` dict (a counter per row, about 70 bytes) by relying on dict insertion order and sorting index hits by position only when needed; (3) skip caching tables that are only ever read in bulk. None is worth doing without a measurement of a real large project (open item 7h in `WRITE_DESIGN.md`).

## Line 204-263 (`_candidates`) — `OR` and short tables scan; index hits are sorted per call
`if use_or or not where or len(rows) < _INDEX_MIN_ROWS: return list(rows.values())` builds a new list of every row dict for each such call, which is what makes an `OR` select O(rows) with a full allocation. For `OR` over non-NULL values the index machinery could be reused: look each column up in its index (building it on first use), union the id sets, then order by `_order`. Memory price is one index per column used with `OR` (about 100-150 bytes per row per column). The `OR` call sites are the point `is_referenced` checks and the rope-pull lookups (see `README.md`, finding 2).
For an indexed hit the result ids are sorted by `_order` on every call (`sorted(narrowest, key=...)`, O(k log k)). k is small for FK lookups, so this is fine; it would matter only for a column whose value is shared by thousands of rows (those are sent to the scan path anyway by `_INDEX_MAX_SHARE = 0.5`).

## Line 163-201 (`select`) — a tuple per match and a re-check of the whole `where`
Every candidate row is re-checked with `_row_matches` (line 53, builds a list of booleans per row) and a tuple is built per match. For the common single-condition lookup that second check is redundant after an index hit; a fast path for a single equality condition on an indexed column would skip `_row_matches`. Saves about 0.3 us per row hit; small.

## Line 404-457 (`change`, `insert`), 520-554 (`update_statements`, `commit_flushed`) — gesture writes
`change` merges into `_updates` and `_revalue`s the indexes for changed indexed columns (line 321). `update_statements` groups updates by column set and sorts, producing one `executemany` per group, which is the efficient shape (`WRITE_DESIGN.md` section 2: 200 rows 0.35 ms as one `executemany` versus 3.7 ms as individual statements). Nothing to change.

## Locking
Reads and index builds take an `RLock` (the circuit dock reads from a worker thread). Uncontended acquire is about 0.1 us; it is on every `select` that reaches `_candidates`.
