# harness_designer/database/global_db/image.py

SQL calls in this module (AST count): 7.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Image.path`: cached after first read.
- `Image.uuid`: cached after first read.
- `Image.file_type_id`: cached after first read.

## Load-time functions
These run when the database is opened or built, not on every interaction.
- `Image.load`.


Status: static read of the code only. Nothing here has been profiled.
