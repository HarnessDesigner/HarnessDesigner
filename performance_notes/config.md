# harness_designer/config.py

## Line 219-239, 260-285 — `_ConfigDB` re-checks table existence on every single config access
`_ConfigDB.__getitem__` (line 260) and `__setitem__` (line 243) both call
`if item not in self:` before returning/creating the table wrapper, and
`__contains__` (line 219) answers that by running
`SELECT [name] FROM sqlite_master WHERE type="table";` and pulling every
table name back to check membership in Python. This runs on every
`ConfigDB.__table__` property access (line 438), which itself is hit by
`__getattribute__` (line 466) and `__setattr__` (line 514) — i.e. on every
single read or write of any `Config.*` attribute anywhere in the app.

Config tables are never dropped at runtime; once a table exists for a given
`__table_name__` it exists for the rest of the process. This is the same
shape as the singleton-cache short-circuit already used for DB entry classes
elsewhere (`PJTCavity`/`Housing`/etc. — see MEMORY.md's "Singleton-cache
short-circuit" entry): cache confirmed-existing table names in a local set
on `_ConfigDB` the first time `__contains__`/`__getitem__` confirms one
exists, and skip the `sqlite_master` query entirely once a name is in that
set. Given every Config read/write in the app goes through this path, this
looks like the highest-value fix in this file.

## Line 120-161 — `_ConfigTable.__setitem__` costs 2 round trips per write (up to 3 on the INSERT path)
Every value write does a `key not in self` existence check (a `SELECT`),
then either an `INSERT` (falling back to `UPDATE` on `IntegrityError`) or an
`UPDATE`. Since `key` is already declared `UNIQUE NOT NULL` (line 251), this
can collapse to one `INSERT OR REPLACE INTO [table] (key, value, decode)
VALUES (?, ?, ?);` — one round trip instead of two, no exception-driven
fallback needed. Matches MEMORY.md's "Database query consolidation"
guidance; worth doing given every `Config.X.attr = value` in the app funnels
through this method via `ConfigDB.__setattr__`.
