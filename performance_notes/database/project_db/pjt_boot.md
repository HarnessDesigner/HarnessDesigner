# harness_designer/database/project_db/pjt_boot.py

Project row class. 3 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Selects by a column other than the id (answered from a lazily built index after the first call): `get_from_position3d_id` (by position3d_id).
