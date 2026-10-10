# harness_designer/database/project_db/pjt_splice.py

SQL calls in this module (AST count): 16.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTSplice.wires`: no cache guard found (queries on every read).
- `PJTSplice.branch_position3d_id`: cached after first read.
- `PJTSplice.branch_position_pegboard_id`: cached after first read.
- `PJTSplice.circuit_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
