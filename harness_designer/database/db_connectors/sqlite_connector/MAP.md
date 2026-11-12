## FILES

#### __init__.py

Package init; no real logic of its own.

#### connector.py

`SQLConnector(ConnectorBase)` plus `_enable_wal()`. **SQLite runs in WAL mode (decided 2026-09-20).** `_enable_wal()` is called right after `sqlite3.connect()` (`journal_mode=WAL`, `synchronous=NORMAL`, the latter only applied if WAL actually took). Why: measured on the user's machine, a default-mode commit costs ~3 ms whether it carries 1 row or 8, and `update()`/`batch_update()`/`insert()` all commit — a live drag was paying ~6-10 commits per mouse move (~20-30 ms of disk waiting per move); with WAL, a commit is ~0.02 ms. Costs accepted as part of that decision: `-wal`/`-shm` sidecar files exist while the app runs (folded back on a clean `close()`, recovered automatically after a crash); copying the `.db` file while the app is running can miss the newest commits — always copy `-wal`/`-shm` alongside it and open the copy `mode=ro`, never the live files, when inspecting a running project's data. After a power failure (not an app crash) the last few commits can be lost, never corruption. Not possible on network shares/read-only files — `_enable_wal` then logs a warning and leaves SQLite's defaults in place. WAL is stored in the database file itself, so it stays on for any other connection that opens the same file (`process/db_broker.py` opens it from another process). The real lever on a hot write path (mouse-move handlers, drags) is the NUMBER OF COMMITS, not row count — batch writes into one `batch_update` rather than one write per row (see `project_db/MAP.md`).

**One cursor per thread (2026-11-11):** `_cursor` is a property: each thread gets its own cursor on the one connection (`check_same_thread=False`). The shared cursor broke a statement of one thread in the middle of another's (`sqlite3.ProgrammingError: Recursive use of cursors not allowed`, or one thread's `fetchall` returning the other's rows). Seen when a housing was dragged while the circuit editor's worker thread (`_BuildWorker`) was reading the project: the lookup of the housing's child points failed after the housing had moved, so the terminals stayed behind (a housing 245 mm from its terminals). Checked with four threads of execute + fetchall (`twist/cursor_thread_test.py`). The in-memory table caches are still not locked.

#### settings_dialog.py

Placeholder module for future SQLite connector settings dialogs — not yet implemented (MySQL's equivalent, `mysql_connector/settings_dialog.py`, is a real dialog; this one has no real content beyond its own docstring).

#### sql_table.py

SQLite-flavored `SQLTable`/`SQLField`/`SQLFieldReference` and field-type subclasses (`PrimaryKeyField`, `UUIDField`, `TextField`, `FloatField`, `BytesField`, `IntField`, ...) — the SQLite-side mirror of `mysql_connector/sql_table.py`'s schema-definition helpers.
