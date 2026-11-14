# harness_designer/database/project_db/pjt_transition_branch.py

Project row class. 10 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `bundle`, `concentric`, `transition_id`, `branch_id`, `diameter`.

3 setters; 3 of them call `PJTTableBase.update`. Outside a gesture that is `UPDATE` + `commit` (about 0.015 ms on WAL) + a cache mirror per write; inside `begin_gesture()` it only changes the cache and is flushed in one transaction on `end_gesture`. Drags and rotations run inside a gesture; anything else that sets several of these properties per user action pays one commit each.

Selects by a column other than the id (answered from a lazily built index after the first call): `bundle` (by start_point3d_id, stop_point3d_id), `concentric` (by transition_branch_id).
