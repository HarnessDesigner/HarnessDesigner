# harness_designer/database/create_database/deratings.py

Table definition and seed data for `deratings` (9 column definitions, 3 foreign key references). Runs at first build and at the startup "does the table need new columns" check, not in any interaction.

This module creates its own secondary index with a raw `CREATE INDEX` (the table-definition helper has no index syntax).

SQL-calling functions: `add_indexes`.
