# harness_designer/database/project_db/pjt_terminal.py

Project row class. 35 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `is_start`, `voltage_drop`, `volts`, `load_type`, `load`, `cavity_id`, `circuit_id`, `seal`, `position2d_id`, `wire_position3d_id`, `wire_position3d_id_raw`, `wire_position_pegboard_id`, `wire_position_pegboard_id_raw`, `wire_position2d_id`, and 7 more.

11 setters; 11 of them call `PJTTableBase.update`. Outside a gesture that is `UPDATE` + `commit` (about 0.015 ms on WAL) + a cache mirror per write; inside `begin_gesture()` it only changes the cache and is flushed in one transaction on `end_gesture`. Drags and rotations run inside a gesture; anything else that sets several of these properties per user action pays one commit each.

Table calls inside a loop: `sync_free_wire_points`. Each is a cache lookup, so this is cheap unless the loop runs per frame over many rows.

Selects by a column other than the id (answered from a lazily built index after the first call): `__check_for_other_starts` (by circuit_id, is_start), `seal` (by terminal_id), `sync_free_wire_points` (by parent_point_id).
