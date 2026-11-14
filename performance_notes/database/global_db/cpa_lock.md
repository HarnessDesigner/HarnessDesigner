# harness_designer/database/global_db/cpa_lock.py

Catalog row class. 4 property getters read through `self._table.select('col', id=...)`, which `TableBase.select` answers from the per-wrapper row cache (one `SELECT` of the whole row when the wrapper is created, dropped when the wrapper is garbage collected). Reads after that are dict lookups; see `database/README.md`.

1 setters; 1 of them call `TableBase.update`, which is one `UPDATE` plus one `commit` (about 0.015 ms on WAL) and refreshes the cached row. Catalog edits are one cell at a time, so no batching is needed.

Direct SQL in this file (`execute`/`executemany`): `get_compat`.

Lookups by a column other than the id go to SQL: `__getitem__` (by part_number). Unique columns (`part_number`, `name`) are indexed; a plain FK column is not (see `database/README.md`, finding 4).
