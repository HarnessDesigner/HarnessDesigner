# harness_designer/database/global_db/file_types.py

SQL calls in this module (AST count): 7.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `FileTypesTable.choices`: no cache guard found (queries on every read).
- `FileType.extension`: cached after first read.
- `FileType.mimetype`: cached after first read.
- `FileType.is_model`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
