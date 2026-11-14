# harness_designer/database/create_database/wire_conductors.py

Table definition and seed data for `wire_conductors` (13 column definitions, 5 foreign key references). Runs at first build and at the startup "does the table need new columns" check, not in any interaction.

This module creates its own secondary index with a raw `CREATE INDEX` (the table-definition helper has no index syntax).

SQL-calling functions: `add_indexes`.
