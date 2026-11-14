# harness_designer/database/id_generator.py

## Line 222-233 (`_LocalMonotonicClock.next_timestamp`), 240-279 (`generate_*_row_id`)
One lock acquire, one `time.time_ns()` and a pack per id. The `sql=2` in the AST count is the MySQL branch, which asks the server for the next id (a network round trip per id; MySQL is not the active backend). On SQLite an id costs a few microseconds. Bulk inserts that generate thousands of ids (a housing with its cavity set) do it in a loop; that is fine.
Ids are 16 bytes, and every FK column in a `pjt_*` row holds one, so the id width drives both the database size and the size of the `TableData` rows (a 16-byte `bytes` object costs 49 bytes in Python). A smaller id would save both, but the scheme (the project id in the leading bytes is what the project-load range scan uses) depends on the width; do not change it for speed.
