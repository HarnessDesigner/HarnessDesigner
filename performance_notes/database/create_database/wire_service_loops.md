# harness_designer/database/create_database/wire_service_loops.py

Table definition and seed data for `pjt_wire_service_loops` (18 column definitions, 6 foreign key references). Runs at first build and at the startup "does the table need new columns" check, not in any interaction.

No secondary index is created for this table; lookups by anything other than the primary key or a `UNIQUE` column are scans. Only matters if the table is large (see `database/README.md`, finding 4, for the measured cost on the big catalog tables).

SQL-calling functions: `add_pjt_wire_service_loop`.
