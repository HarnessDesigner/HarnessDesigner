# harness_designer/database/global_db/cavity_lock.py

Catalog row class. 1 property getters read through `self._table.select('col', id=...)`, which `TableBase.select` answers from the per-wrapper row cache (one `SELECT` of the whole row when the wrapper is created, dropped when the wrapper is garbage collected). Reads after that are dict lookups; see `database/README.md`.

Getters without the `DefaultStoredValue` guard (a `select` call on every read, still a dict lookup for a cached row): `choices`.

Direct SQL in this file (`execute`/`executemany`): `choices`.

Calls inside a loop (one query per iteration, check the row count): `choices`.

Lookups by a column other than the id go to SQL: `__getitem__` (by name). Unique columns (`part_number`, `name`) are indexed; a plain FK column is not (see `database/README.md`, finding 4).
