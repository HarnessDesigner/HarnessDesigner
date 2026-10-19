## FILES

#### __init__.py

Package init; no real logic of its own.

#### connector.py

`SQLConnector(ConnectorBase)` — the real connector implementation, plus `LoginDialog` (Qt login UI for connecting to the server).

#### row_id_functions.py

DDL for the MySQL-side row-id generation mechanism — the server-side counterpart of `database/id_generator.py`'s client-side SQLite generation (`next_project_row_id`). Row ids are generated differently per backend: SQLite ids come from the client, MySQL ids come from the server here. If a second id-generating process is ever introduced, both sides of this split need re-checking together, not just one (see MEMORY.md's "Project row-id collision safety" note).

#### settings_dialog.py

`SQLOptionsDialog` — Qt dialog for editing MySQL connector settings (host/port/credentials), plus a `_file_browse_button` helper.

#### sql_table.py

MySQL-flavored `SQLTable`/`SQLField`/`SQLFieldReference` and field-type subclasses (`PrimaryKeyField`, `UUIDField`, `TextField`, `FloatField`, `BytesField`, ...) — the schema-definition building blocks `create_database/*.py` modules use when the table targets this backend.
