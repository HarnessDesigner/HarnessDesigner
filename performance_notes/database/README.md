# performance_notes/database

Covers `harness_designer/database/`. Each module has its own note in this tree, written from an AST count of its SQL calls, property getters and loops. The `__init__.py` files hold no code and have no notes.

## Patterns that matter across the folder

**Property reads go to SQL unless cached.** Most global and project entry classes expose columns as properties. Each property getter calls the table (`select`, through `TableBase.select` or `PJTTableBase.select`). The getters that have the `_stored_*` / `DefaultStoredValue` guard keep the value after the first read, so only the first read per object queries the database. Getters without that guard query on every read. The per-module notes list both kinds.

**Seeding is per row.** The `create_database/*.py` modules insert the built-in catalogue. Every `add_*` helper calls one or more `get_*_id` lookups, and each lookup is its own `SELECT`. The seeding runs only when a table is empty: each module's `add_records` first runs `SELECT 1 ... LIMIT 1` and returns early when rows exist. The cost is therefore paid once, on the first build. Caching the lookup ids in a dict would cut the query count, but this is a one-time cost and is not worth changing without a measurement.

**Row ids are generated per row.** `id_generator.generate_global_row_id` and `generate_project_row_id` run once per inserted row. On SQLite they take an in-process lock. On MySQL they call a stored function. Both are cheap per call, so this matters only during seeding.

**Callbacks and weak references.** `common_db/callback.py` and the `_instances` registries in `global_db/bases.py` and `project_db/pjt_bases.py` hold weak references. Every `_populate` walks the callback list. Fine for the sizes seen here. Not profiled.

**Metaclass registries.** `_EntrySingleton` and `_PJTEntrySingleton` keep one instance per id in `_instances`, guarded by a lock. Every entry construction and lookup takes that lock.

## Known issues found during this review (not fixed here)

- `db_connectors/mysql_connector/settings_dialog.py`: `getattr(Config, 'kerberos_auth_mode', 'SSPI')` reads a name that `config.py` defines inside the nested `mysql` class, not on `Config` itself. The lookup likely always returns `'SSPI'`. This is a functional question, not a performance one.
- `project_db/pjt_bases.py` `PJTTables.tables` builds its list by reflecting over `dir(self)` on every access. It is a candidate for a fixed list if it is read often.

## Remaining `getattr` / `setattr` / `hasattr` (8 calls)

The color and plating mixins no longer use reflection. They take explicit accessor functions (`SetTarget`), and `WireControl` passes accessors for the stripe color and the core material. The sites below are kept because the name comes from data, or because the check tests a real type:

- `global_db/ip/fluid.py`, `global_db/ip/solid.py`: `getattr(_image.ip, f'IPX{self.name}')`. The rating name comes from the database row.
- `db_connectors/mysql_connector/settings_dialog.py`: `getattr(mysql.connector.constants.ClientFlag, name)`. The flag name comes from the stored settings.
- `db_connectors/mysql_connector/connector.py`: `setattr(Config, key, value)`. The key comes from the caller.
- `project_db/mixins/angle3d_lock.py`: `hasattr(obj, 'lock_angle')` and `hasattr(obj, 'unlock_angle')`. Only `objects/note.py` defines these methods, so this is a type test in disguise. An `isinstance` against the note facade would say so directly, but that import would add a dependency from the database layer on the objects layer.
- `project_db/pjt_bases.py`: `getattr(self, name)` in `PJTTables.tables`. It collects every attribute ending in `_table`.

A separate finding: `db_connectors/mysql_connector/settings_dialog.py` reads `getattr(Config, 'kerberos_auth_mode', 'SSPI')`. That attribute is defined inside the nested `mysql` class, so the lookup probably always returns `'SSPI'`. It is a functional question and was left unchanged.
