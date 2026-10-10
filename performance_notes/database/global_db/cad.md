# harness_designer/database/global_db/cad.py

SQL calls in this module (AST count): 7.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `CAD.path`: cached after first read.
- `CAD.uuid`: cached after first read.
- `CAD.file_type_id`: cached after first read.

## Load-time functions
These run when the database is opened or built, not on every interaction.
- `CAD.load`.


Status: static read of the code only. Nothing here has been profiled.
