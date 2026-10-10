# harness_designer/database/project_db/pjt_concentric.py

SQL calls in this module (AST count): 5.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTConcentric.layers`: no cache guard found (queries on every read).
- `PJTConcentric.bundle_id`: cached after first read.
- `PJTConcentric.transition_branch_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
