# harness_designer/database/config_db.py

Not used. `dep_trace --imported-by` finds no importer: `config.py` defines its own `_ConfigTable` and `_ConfigDB`, and nothing imports this module. It costs nothing at runtime because it is never imported, but it is a second copy of the same SQLite settings code that can drift from the live one (see `performance_notes/config.md` for the live code's findings: a `sqlite_master` query per table access and one commit per saved setting). Delete it once you are sure nothing outside the repo imports it, or move any difference into `config.py`.
