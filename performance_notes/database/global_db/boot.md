# harness_designer/database/global_db/boot.py

Catalog row class. 2 property getters read through `self._table.select('col', id=...)`, which `TableBase.select` answers from the per-wrapper row cache (one `SELECT` of the whole row when the wrapper is created, dropped when the wrapper is garbage collected). Reads after that are dict lookups; see `database/README.md`.

Direct SQL in this file (`execute`/`executemany`): `get_compat`.

Lookups by a column other than the id go to SQL: `__getitem__` (by part_number). Unique columns (`part_number`, `name`) are indexed; a plain FK column is not (see `database/README.md`, finding 4).
