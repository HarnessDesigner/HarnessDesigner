## FILES

#### __init__.py

Package init for `database`; no real logic of its own. Everything that talks to a database lives under this package: two SQL backends (SQLite for a local project, MySQL for the shared parts catalog server) sit behind one connector abstraction in `db_connectors/`, with two independent schemas on top of it — the shared parts catalog (`global_db/`, table names singular) and the per-project data (`project_db/`, table names prefixed `pjt_`) — plus the DDL/seed layer that creates and populates both (`create_database/`, one file per table, plural names). There is exactly ONE connector/connection for the whole running app: the catalog (`GLBTables`) and the open project (`PJTTables`) share the same SQLite file and connection, which matters for WAL mode (see `db_connectors/sqlite_connector/MAP.md`).

#### config_db.py

`ConfigTable`/`ConfigDB` — the SQLite-backed implementation behind `harness_designer.config.Config`. This backs a LIVE database, not a fixture: `Config.*` nested classes (e.g. `Config.logging`) use the `ConfigDB(type)` metaclass, whose `__setattr__` writes through to the real `%APPDATA%\HarnessDesigner\config.db` on **every** non-underscore attribute assignment, indistinguishable from a change made through the running app. A bare `import harness_designer` triggers `Config.open()` and constructs the logger singleton at import time, so even a throwaway "does it import" script pollutes the user's real config/log files unless `USERPROFILE`/`HOME` is sandboxed to a scratch directory first (and `get_appdata()` needs `<scratch>/appdata/roaming` pre-created — it uses a non-recursive `os.mkdir`). Never read/assign `Config.*` attributes in a throwaway script.

#### id_generator.py

Client-side generation of the 128-bit row-id scheme used by `pjt_*` tables — `pack_project_row_id`/`pack_global_row_id` and their `unpack_*` counterparts (project id, timestamp, version, user id packed into one id), plus `_LocalMonotonicClock` (lock-serialized, nanosecond-bumping clock used as the timestamp component) and `generate_project_row_id`/`generate_global_row_id`. This is the file this file's DESIGN NOTES's "Project row-id collision safety" note is about: on SQLite every id comes from the clock, which takes a `threading.Lock` and bumps by 1 ns on a tie or a backward clock, so ids are unique within a process even under free-threaded Python; MySQL ids instead come from the server (`db_connectors/mysql_connector/row_id_functions.py`'s `next_project_row_id`). Only a second id-generating process (none exists today) would need this revisited.

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

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### The sibling database repo builds the downloaded global database: keep it aligned (2026-10-17)
`C:\Users\drsch\PycharmProjects\harness_designer_database` (CI: `.github/workflows/build-database.yml`) builds the SQLite file the app downloads on first run. It builds ONLY the global tables (the modules in `builder/build_database.py`'s `TABLE_MODULES`), never `pjt_*`. Its `builder/create_database/*.py` and `builder/sql_table.py` are ported from this repo's `database/create_database/*.py` and `db_connectors/sqlite_connector/sql_table.py`, so a global table's `table = _con.SQLTable(...)` must read the same in both repos. Any new GLOBAL column or table must be mirrored there (project-side `pjt_*` ones need not; the sibling's `pjt_*` definitions are old, never-built copies).
- Every foreign key is `ON UPDATE NO ACTION` (the app does cascade/cleanup in Python); `ON DELETE SET DEFAULT`, except `transition_branches.transition_id` which is `NO ACTION` for both. `PRAGMA foreign_keys` is off, so FK actions are descriptive only. Default strings in table definitions use single quotes (`default="'[0.0, 0.0, 0.0]'"`).
- In the catalog JSON the entry with `"id": 0` is stored with the nil UUID (`X'00..00'`, what an unassigned FK defaults to); every other entry gets a generated id. The sibling's lookup/IP tables load from `Universal/*.json` via `builder/seed_json.py` (accessories is still hard-coded); the `"id": 0` rows are the defaults ("No Family", "No Series", "Unknown Material", "Unknown", "No Lock", "No Protection", IP "0 / No Protection" and rating "IP00") and are seeded before the part loaders; `bulk_insert.insert_data` ignores blank names so a blank resolves to the default row. A fresh build has `PRAGMA foreign_key_check` = 0. Databases already downloaded are not repaired.
- `wire_types` (2026-10-18, user's design): global lookup (`id` UUID, unique `name`) and `wires.wire_type_id` (nil default). The nil row is "Wire"; "Coaxial" and "Ribbon" are the others; `get_wire_type_id` creates any other name. The app side is the full lookup fan-out (`global_db/wire_type.py`, `mixins/wire_type.py`, `GLBTables` registration, `search_items`, DB editor column). The app no longer self-seeds it: an old downloaded DB missing the table gets it created empty and needs a fresh full-DB download.
- `resource_state` is a global table the app creates itself on first run (empty); `app_users` and `used_parts` are unused.
- **How to check alignment:** render each side's `CREATE TABLE` with its own `SQLTable` classes under a stub top-level package (neither repo's `__init__` runs) and diff column by column, with a scratch script, not a unit test. Several app modules import `harness_designer.database` absolutely and an old installed copy of `harness_designer` sits in `C:\python3.11.14\Lib\site-packages`, so alias that name to the stub package.

#### Project row-id collision safety (checked 2026-10-06)
Project row ids are generated client-side in `database/id_generator.py` (SQLite) and by the server (MySQL, `next_project_row_id`). On SQLite every id comes from `_LocalMonotonicClock.next_timestamp()`, which takes a `threading.Lock` and bumps by 1 ns on a tie or backward clock, so ids are unique within a process (including free-threaded Python). Only the main app creates project rows (`process/` imports none of the project-db or id code), one at a time per user action. The clock is not 1 ns (`time.time_ns()` changes about every 1 ms here), so two processes generating ids in one tick could collide, but nothing does. `uuid.uuid4()` ids (cavity/housing/angle/color rows) are random 122-bit and do not use the lock. If a second process ever creates project rows, revisit: use the 20 reserved bits as a per-process tag, or a finer clock.

#### Part scrapers live in the sibling repo (`scrapers/`; Molex built 2026-10-18, Yazaki and KET the same night)
`harness_designer_database\scrapers\<name>\` has `collect.py` (downloads to git-ignored `raw/`) and `convert.py` (writes `<Manufacturer>/*.json`, picked up by the builder's folder-walking loaders like `Aptiv/`, `Bosch/`, `TE/`). Yazaki/KET use the shared `scrapers/common.py` (row templates via `new_row`, `Catalog` checks against the `Universal` lookup tables, `fill_compat`, `write_rows`); Molex predates it. `scrapers/README.md` has the status table. A scratch build of Molex + Yazaki + KET has 0 warnings and `PRAGMA foreign_key_check` = 0. The builder was extended for it (`create_database/accessories.py` `add_json_records`, called from `build_database.py`).
- **Molex:** molex.com is behind bot protection, but part lists come from `https://search.molex.com/api/search/products-per-category?q=<name>&rows=<up to 2000>&sort=id asc&fq=materialMaster.promotable:("true")` (narrow with `fq=taxonomyPathValueLast:"Splices"`), no cookies; `productdetails?q=<pn>` adds `useWith*`/`matesWith*` that `convert.py` expands into `compat_*`. Scope (user): housings, PCB headers/receptacles, crimp/ring/spade terminals and quick disconnects, splices, accessories by `general.componentType` (TPA/ISL -> tpa_locks, CPA, covers, boots, wire seals/gaskets/cavity plugs -> seals, dummy housings, rest -> `accessories.json`), heat shrink -> `bundles.json`, flat/industrial/coaxial cable -> wires with `wire_type` Ribbon/Wire/Coaxial. Left out: I/O, board-to-board, FFC, RF, D-Sub, backplane, terminal blocks, heavy-duty and circular. Mapping: part number = `productNumberDisplay` (no dash); Plug/Receptacle -> Male/Female; PCB orientation Right Angle -> "90°", Vertical -> "Straight"; unmapped colours are reported (`COLORS` in `convert.py`), never invented. model3d is a `*_stp.zip` served as `application/zip`, which `resources.py` unzips (keeps the first member with a known extension).
- **Yazaki** (`connector.yazaki-group.com`, 2,477 parts): `POST /cgi-bin/english/search.cgi` returns the result set as `var mst = [...]`; one query per `accessory1..4` checkbox splits holders from covers; `detail.cgi?part_id=` has dimensions, mating parts and what a housing takes. No datasheet or 3D model. **KET** (`ket.com/en`, 5,356 parts): needs the session cookie from `/kr/changeLang.ket?language=en`; `POST /en/product/feature-search.ket` gives 20 records per page. Its STEP/image links (`/cm/fileDownMan.ket?attcFilSn=N`) are extension-less `application/octet-stream`, and `resources.py` only accepts a download with a known content type or extension in its address, so `convert.py` appends `&file=<part>.stp`.
- **Not built (details in `scrapers/README.md`):** Amphenol (GraphQL answers 403), JAE, Wurth and amphenol.com (bot protection, deliberately not worked around), Harting (key from the page config), Radiall, Rosenberger, ITT Cannon, Glenair, FIT/Foxconn (nothing open), and corporate/cable-assembly sites with nothing to scrape.
