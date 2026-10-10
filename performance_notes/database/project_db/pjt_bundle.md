# harness_designer/database/project_db/pjt_bundle.py

SQL calls in this module (AST count): 8.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTBundle.concentric`: cached after first read.
- `PJTBundle.start_layout`: no cache guard found (queries on every read).
- `PJTBundle.stop_layout`: no cache guard found (queries on every read).

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTBundle.delete`.


Status: static read of the code only. Nothing here has been profiled.
