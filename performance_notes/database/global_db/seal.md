# harness_designer/database/global_db/seal.py

SQL calls in this module (AST count): 23.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Seal.scale`: cached after first read.
- `Seal.o_dia`: cached after first read.
- `Seal.i_dia`: cached after first read.
- `Seal.type_id`: cached after first read.
- `Seal.hardness`: cached after first read.
- `Seal.lubricant`: cached after first read.
- `Seal.wire_dia_min`: cached after first read.
- `Seal.wire_dia_max`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
