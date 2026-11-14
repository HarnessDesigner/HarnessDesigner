# harness_designer/database/project_db/pjt_cable.py

Project row class. 18 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `start_split_mm`, `stop_split_mm`, `roll_deg`, `bg_color`, `start_shield_splice_id`, `stop_shield_splice_id`, `shield_clipped`.

7 setters; 7 of them call `PJTTableBase.update`. Outside a gesture that is `UPDATE` + `commit` (about 0.015 ms on WAL) + a cache mirror per write; inside `begin_gesture()` it only changes the cache and is flushed in one transaction on `end_gesture`. Drags and rotations run inside a gesture; anything else that sets several of these properties per user action pays one commit each.

Table calls inside a loop: `next_bg_color`. Each is a cache lookup, so this is cheap unless the loop runs per frame over many rows.
