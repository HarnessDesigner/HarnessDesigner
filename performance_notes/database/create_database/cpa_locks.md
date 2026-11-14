# harness_designer/database/create_database/cpa_locks.py

Table definition and seed data for `cpa_locks` (21 column definitions, 11 foreign key references), `pjt_cpa_locks` (11 column definitions, 4 foreign key references). Runs at first build and at the startup "does the table need new columns" check, not in any interaction.

Seeding only happens when the table is empty (`add_records` checks first), so the per-row `get_*_id` lookups and inserts are a one-time cost. Not worth batching.

No secondary index is created for this table; lookups by anything other than the primary key or a `UNIQUE` column are scans. Only matters if the table is large (see `database/README.md`, finding 4, for the measured cost on the big catalog tables).

SQL-calling functions: `add_cpa_lock`.
