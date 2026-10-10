# harness_designer/database/global_db/splice.py

SQL calls in this module (AST count): 13.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Splice.type_id`: cached after first read.
- `Splice.resistance`: cached after first read.
- `Splice.min_dia`: cached after first read.
- `Splice.max_dia`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
