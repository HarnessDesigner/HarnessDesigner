## FILES

#### __init__.py

Package init; no real logic of its own.

#### base.py

`ConnectorBase` — abstract base wrapping a `con`+`cursor` pair, the common surface both concrete connectors (`mysql_connector/`, `sqlite_connector/`) implement.

#### db_data.py

`DBData` — helpers for downloading and unpacking bundled database seed data.

## FOLDERS

#### mysql_connector/

MySQL backend for the shared parts-catalog server — see `mysql_connector/MAP.md`.

#### sqlite_connector/

SQLite backend for the local project database — see `sqlite_connector/MAP.md`. There is exactly ONE connector/connection for the whole running app: the parts catalog (`GLBTables`) and the open project (`PJTTables`) live in the same SQLite file on the same connection, not separate connections per schema. This is why the WAL-mode decision (see `sqlite_connector/MAP.md`) is app-wide, not project-only.
