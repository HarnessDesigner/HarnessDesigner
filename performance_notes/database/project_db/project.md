# harness_designer/database/project_db/project.py

Project row class. 9 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

7 setters; 7 of them call `PJTTableBase.update`. Outside a gesture that is `UPDATE` + `commit` (about 0.015 ms on WAL) + a cache mirror per write; inside `begin_gesture()` it only changes the cache and is flushed in one transaction on `end_gesture`. Drags and rotations run inside a gesture; anything else that sets several of these properties per user action pays one commit each.

Raw SQL through the connector in this file, which bypasses the in-memory store (it reads the database, so it does not see changes made inside an open gesture, and it costs a real query each time): `_read_column`.
