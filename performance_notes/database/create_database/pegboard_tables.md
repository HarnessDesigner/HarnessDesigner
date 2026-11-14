# harness_designer/database/create_database/pegboard_tables.py

Table definition and seed data for `pjt_pegboard_tables` (5 column definitions, 1 foreign key references). Runs at first build and at the startup "does the table need new columns" check, not in any interaction.

No secondary index is created for this table; lookups by anything other than the primary key or a `UNIQUE` column are scans. Only matters if the table is large (see `database/README.md`, finding 4, for the measured cost on the big catalog tables).
