# harness_designer/database/global_db/wire_conductor.py

Catalog row class. 57 property getters read through `self._table.select('col', id=...)`, which `TableBase.select` answers from the per-wrapper row cache (one `SELECT` of the whole row when the wrapper is created, dropped when the wrapper is garbage collected). Reads after that are dict lookups; see `database/README.md`.

Getters without the `DefaultStoredValue` guard (a `select` call on every read, still a dict lookup for a cached row): `stripe_color_id`, `core_material_id`, `strands`, `conductor_dia_mm`, `size_mm2`, `size_awg`, `od_mm`, `stored_od_mm`.

7 setters; 7 of them call `TableBase.update`, which is one `UPDATE` plus one `commit` (about 0.015 ms on WAL) and refreshes the cached row. Catalog edits are one cell at a time, so no batching is needed.

Direct SQL in this file (`execute`/`executemany`): `for_wire`.
