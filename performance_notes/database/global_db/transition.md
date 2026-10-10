# harness_designer/database/global_db/transition.py

SQL calls in this module (AST count): 8.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Transition.branch_count`: cached after first read.
- `Transition.branches`: cached after first read.
- `Transition.shape_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
