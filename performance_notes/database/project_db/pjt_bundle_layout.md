# harness_designer/database/project_db/pjt_bundle_layout.py

Project row class. 8 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `position3d_id`, `position_pegboard_id`, `attached_bundles`.

2 setters; 2 of them call `PJTTableBase.update`. Outside a gesture that is `UPDATE` + `commit` (about 0.015 ms on WAL) + a cache mirror per write; inside `begin_gesture()` it only changes the cache and is flushed in one transaction on `end_gesture`. Drags and rotations run inside a gesture; anything else that sets several of these properties per user action pays one commit each.

`select(..., OR=True)` call sites: `attached_bundles`. An `OR` select scans every cached row of the table (about 0.4 us per row; see `table_data.md`).

Selects by a column other than the id (answered from a lazily built index after the first call): `for_point_pegboard_id` (by point_pegboard_id), `get_from_position3d_id` (by point3d_id).
