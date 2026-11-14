# harness_designer/database/project_db/pjt_bundle.py

Project row class. 14 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `concentric`, `start_layout`, `stop_layout`.

Table calls inside a loop: `delete`. Each is a cache lookup, so this is cheap unless the loop runs per frame over many rows.

Selects by a column other than the id (answered from a lazily built index after the first call): `concentric` (by bundle_id), `delete` (by point3d_id, point_pegboard_id), `start_layout` (by point3d_id), `stop_layout` (by point3d_id).
