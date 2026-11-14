# harness_designer/database/global_db/mixins/temperature.py

Column mixin. 4 property getters read through `self._table.select('col', id=...)`, which `TableBase.select` answers from the per-wrapper row cache (one `SELECT` of the whole row when the wrapper is created, dropped when the wrapper is garbage collected). Reads after that are dict lookups; see `database/README.md`.

2 setters; 2 of them call `TableBase.update`, which is one `UPDATE` plus one `commit` (about 0.015 ms on WAL) and refreshes the cached row. Catalog edits are one cell at a time, so no batching is needed.

Direct SQL in this file (`execute`/`executemany`): `_on_max_temp`, `_on_min_temp`, `set_obj`.
