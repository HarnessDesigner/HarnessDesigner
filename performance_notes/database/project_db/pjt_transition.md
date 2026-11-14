# harness_designer/database/project_db/pjt_transition.py

Project row class. 14 property getters read through `self._table.select('col', id=...)`, which is a dict lookup in the table's in-memory `TableData` (no SQL; see `database/project_db/table_data.md`). The `_stored_*` / `DefaultStoredValue` guard, where present, saves only the call overhead.

Getters that call `select` on every read (no stored-value guard; each is one dict lookup, but chains of them add up in a per-frame loop): `branch1`, `branch2`, `branch3`, `branch4`, `branch5`, `branch6`.

Selects by a column other than the id (answered from a lazily built index after the first call): `branch1` (by branch_id, transition_id), `branch2` (by branch_id, transition_id), `branch3` (by branch_id, transition_id), `branch4` (by branch_id, transition_id), `branch5` (by branch_id, transition_id), `branch6` (by branch_id, transition_id).
