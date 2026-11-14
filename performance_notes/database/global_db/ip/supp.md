# harness_designer/database/global_db/ip/supp.py

Lookups by a column other than the id go to SQL: `__getitem__` (by name). Unique columns (`part_number`, `name`) are indexed; a plain FK column is not (see `database/README.md`, finding 4).
