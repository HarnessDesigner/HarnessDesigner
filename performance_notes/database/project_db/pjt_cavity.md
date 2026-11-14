# harness_designer/database/project_db/pjt_cavity.py

Project row class. 22 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `terminal`, `terminal_position3d_id`, `wire_position3d_id`, `wire_position3d_id_raw`, `terminal_position_pegboard_id`, `wire_position_pegboard_id`, `wire_position_pegboard_id_raw`, `seal`, `angle3d`.

7 setters; 6 of them call `PJTTableBase.update`. Outside a gesture that is `UPDATE` + `commit` (about 0.015 ms on WAL) + a cache mirror per write; inside `begin_gesture()` it only changes the cache and is flushed in one transaction on `end_gesture`. Drags and rotations run inside a gesture; anything else that sets several of these properties per user action pays one commit each.

Selects by a column other than the id (answered from a lazily built index after the first call): `get_from_position2d_id` (by position2d_id), `get_from_position3d_id` (by position3d_id, terminal_position3d_id), `seal` (by cavity_id), `terminal` (by cavity_id).
