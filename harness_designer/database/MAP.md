## FILES

#### __init__.py

Package init for `database`; no real logic of its own. Everything that talks to a database lives under this package: two SQL backends (SQLite for a local project, MySQL for the shared parts catalog server) sit behind one connector abstraction in `db_connectors/`, with two independent schemas on top of it — the shared parts catalog (`global_db/`, table names singular) and the per-project data (`project_db/`, table names prefixed `pjt_`) — plus the DDL/seed layer that creates and populates both (`create_database/`, one file per table, plural names). There is exactly ONE connector/connection for the whole running app: the catalog (`GLBTables`) and the open project (`PJTTables`) share the same SQLite file and connection, which matters for WAL mode (see `db_connectors/sqlite_connector/MAP.md`).

#### config_db.py

`ConfigTable`/`ConfigDB` — the SQLite-backed implementation behind `harness_designer.config.Config`. This backs a LIVE database, not a fixture: `Config.*` nested classes (e.g. `Config.logging`) use the `ConfigDB(type)` metaclass, whose `__setattr__` writes through to the real `%APPDATA%\HarnessDesigner\config.db` on **every** non-underscore attribute assignment, indistinguishable from a change made through the running app. A bare `import harness_designer` triggers `Config.open()` and constructs the logger singleton at import time, so even a throwaway "does it import" script pollutes the user's real config/log files unless `USERPROFILE`/`HOME` is sandboxed to a scratch directory first (and `get_appdata()` needs `<scratch>/appdata/roaming` pre-created — it uses a non-recursive `os.mkdir`). Never read/assign `Config.*` attributes in a throwaway script.

#### id_generator.py

Client-side generation of the 128-bit row-id scheme used by `pjt_*` tables — `pack_project_row_id`/`pack_global_row_id` and their `unpack_*` counterparts (project id, timestamp, version, user id packed into one id), plus `_LocalMonotonicClock` (lock-serialized, nanosecond-bumping clock used as the timestamp component) and `generate_project_row_id`/`generate_global_row_id`. This is the file MEMORY.md's "Project row-id collision safety" note is about: on SQLite every id comes from the clock, which takes a `threading.Lock` and bumps by 1 ns on a tie or a backward clock, so ids are unique within a process even under free-threaded Python; MySQL ids instead come from the server (`db_connectors/mysql_connector/row_id_functions.py`'s `next_project_row_id`). Only a second id-generating process (none exists today) would need this revisited.

#### utils.py

Identifier-parsing helpers (`enumerate_alpha`/`get_cavity_ids`, for expanding catalog part-number ranges like cavity ID lists) and `purge_stale_files(db)`, a file-maintenance sweep over `GLBTables`.

## FOLDERS

#### common_db/

Small plumbing shared by both schemas' row/table classes — `CallbackMixin` (mixed into both `global_db/bases.py`'s `EntryBase` and `project_db/pjt_bases.py`'s `PJTEntryBase`) and lazy per-tab DB table loading. See `common_db/MAP.md`.

#### create_database/

DDL/seed layer: one file per table, plural names. This is one layer of a "same-name modules" pipeline that runs, for a given part type: `create_database` (DDL/seed, plural) → `global_db` (catalog part, singular) → `project_db` (placed project instance, `pjt_`-prefixed, FK to the catalog part) → `objects/` (scene wrapper) — see `project_db/MAP.md` for the full diagram. See `create_database/MAP.md`.

#### db_connectors/

Backend-agnostic connector abstraction (SQLite + MySQL) that both schemas below sit on top of. See `db_connectors/MAP.md`.

#### global_db/

The shared parts catalog: one file per entity, table names singular (`housing`, `wire`, ...) — created/seeded by `create_database/` and referenced by a FK from the corresponding `project_db/pjt_*` row (a placed instance points at its catalog part via `part_id`). See `global_db/MAP.md`.

#### project_db/

Per-project `pjt_*` tables — the placed-instance layer of the pipeline (position/angle/scale + a FK to the matching `global_db` catalog part). See `project_db/MAP.md`.
