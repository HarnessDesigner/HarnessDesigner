# harness_designer/config.py

Config is read constantly (every canvas reads `Config.editor_3d.*` per frame) but written rarely (UI change, startup load, shutdown save). The read path is the one that matters; the DB paths only matter at startup and shutdown.

## Line 507-536 (`ConfigDB.__getattribute__`) — debug-call arguments are built on every read even though debugging is off
`DEBUG_CONFIG = False` (line 26), but the call `DEBUG('type.__getattribute__:', cls.__table_name__, cls.__name__, item, repr(value), '\n')` evaluates its arguments BEFORE `DEBUG` can return early: that is one `__table_name__` property call (a `__qualname__` read plus `str.replace`, line 444), one `repr(value)` and a 6-tuple per read. The same pattern is in `__setattr__` (line 555), `__getitem__` (line 489) and `_save`.
Persisted values are copied onto the class by `_load` at startup, so a normal read ends at `type.__getattribute__` (cheap) and never reaches SQLite. The `DEBUG` argument cost is therefore the dominant cost of a config read, and `Config.editor_3d.renderer.x` makes three of them (one per metaclass level).
Fix: guard the call sites with `if DEBUG_CONFIG:` (or delete the debug calls). No memory cost. Worth doing because it sits on the per-frame path; the saving is small per read but the count is large. A `repr()` of a large value (a list or dict setting) is the expensive case.

## Line 233-254 (`_ConfigDB.__contains__`) — pulls every table name from `sqlite_master` to test one name
Each call runs `SELECT [name] FROM sqlite_master WHERE type="table"`, builds a Python list and tests membership. `__getitem__` (line 274) and `__setitem__` (line 257) call it first, so every `ConfigDB.__table__` access on a write or a startup load pays it. Tables are never dropped at runtime, so a local `set` of names already confirmed (filled on the first positive answer) removes the query completely. Cost: one small set of strings, negligible memory.

## Line 380-402 (`ConfigDB._load`) — 3 to 4 queries per setting at startup
For each non-underscore attribute of each registered config class it runs `cls.__table_name__ in ConfigDB.__db__` (a `sqlite_master` scan), `key in cls.__table__` (SELECT), then `cls.__table__[key]` (another SELECT plus an `eval(value)`), all under the module lock. With several hundred settings in `Config` this is a few thousand queries on the startup path. One `SELECT key, value, decode FROM [table]` per class, applied in a loop, is one query per class. No extra memory beyond the fetched rows (transient).

## Line 123-165 (`_ConfigTable.__setitem__`) and `ConfigDB._save` (shutdown) — one commit per setting
Every write does a `key in self` SELECT and then an INSERT/UPDATE followed by its own `commit()`. `ConfigDB.close()` calls `_save()` for every class and `_save` writes every attribute with that path. A shutdown therefore does one commit per setting (hundreds), and a commit is what costs on disk (see MEMORY.md, "SQLite runs in WAL mode ... commits cost per COMMIT"; `config.db` is a separate plain connection with no WAL pragma set here, so each commit is a real fsync).
Fix: wrap `_save` in a single transaction (`executemany` of `INSERT OR REPLACE`), which also removes the SELECT-then-write pair. Saves shutdown time; costs nothing in memory. For the single-setting UI path the 2 round trips are not worth touching.

## Line 92-120 (`_ConfigTable.__getitem__`) — `eval()` on every stored value
Values are stored as `str(value)` and revived with `eval`. Fine for load (one pass), and only reached for attributes not already on the class, so it is not a runtime cost today. Mentioned so nobody moves a hot read onto this path.

## Memory
`Config` holds plain class attributes, no per-read caching. The `ConfigDB.__callbacks__` map keeps weak method references only. Nothing here is a memory concern.
