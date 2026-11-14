# harness_designer/database/db_connectors/sqlite_connector/sql_table.py

DDL helpers. They run at first build and at each startup's "does the table need new columns" check, never in an interaction.

## Line 69-107 (`is_ok`, `update_fields`) — one `pragma_table_xinfo` query per table per startup, parsed with `eval`
For each of the roughly 80 tables it runs `SELECT group_concat(name...) FROM pragma_table_xinfo(...)` and `eval`s the string to get the column names: about 80 small queries at startup (tens of milliseconds in total). It could use one `PRAGMA table_xinfo` per table without `eval`; the saving is small.

## Line 222-253 (`SQLField.__str__`) — no index syntax at all
A field definition supports `PRIMARY KEY`, `UNIQUE`, `NOT NULL`, `DEFAULT` and a foreign-key reference, and nothing else. Secondary indexes cannot be declared from a table definition; the four that exist (`deratings`, `wire_conductors`) are created with raw `CREATE INDEX` in their `create_database` modules. If indexes are added to the catalog tables (`database/README.md`, finding 4) the simplest fit is a small `SQLTable.indexes` list created in `add_to_db` and in `update_fields`, so databases that were already downloaded get them too.

## Line 110-132 (`add_to_db`)
Builds the `CREATE TABLE` string and commits; one commit per table at first build. Fine.
