# harness_designer/database/create_database/transitions.py

Table definition and seed data for `transitions` (18 column definitions, 12 foreign key references), `pjt_transitions` (14 column definitions, 4 foreign key references). Runs at first build and at the startup "does the table need new columns" check, not in any interaction.

Seeding only happens when the table is empty (`add_records` checks first), so the per-row `get_*_id` lookups and inserts are a one-time cost. Not worth batching.

No secondary index is created for this table; lookups by anything other than the primary key or a `UNIQUE` column are scans. Only matters if the table is large (see `database/README.md`, finding 4, for the measured cost on the big catalog tables).

SQL-calling functions: `add_pjt_transition`, `add_transition`.
