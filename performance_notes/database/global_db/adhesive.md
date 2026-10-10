# harness_designer/database/global_db/adhesive.py

SQL calls in this module (AST count): 6.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Adhesive.code`: cached after first read.
- `Adhesive.accessory_part_nums`: cached after first read.
- `Adhesive.accessories`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
