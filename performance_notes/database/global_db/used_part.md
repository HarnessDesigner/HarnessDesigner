# harness_designer/database/global_db/used_part.py

SQL calls in this module (AST count): 5.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `UsedPart.housing_id`: cached after first read.
- `UsedPart.tpa_lock_id`: cached after first read.
- `UsedPart.cpa_lock_id`: cached after first read.
- `UsedPart.cover_id`: cached after first read.
- `UsedPart.terminal_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
