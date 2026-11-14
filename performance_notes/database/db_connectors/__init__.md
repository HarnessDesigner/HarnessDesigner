# harness_designer/database/db_connectors/__init__.py

Picks the SQLite or MySQL connector once, at import, from `Config.database.connector`, and re-exports the same 14 names from whichever module was chosen. No per-call cost. Only the chosen backend is imported, so the other backend's module (and `mysql.connector`) is never loaded; keep it that way, since `mysql-connector-python` is a heavy import.
The choice is made when this module is first imported and cannot change in the same process, so a connector change in settings needs a restart.
