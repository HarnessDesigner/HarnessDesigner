# harness_designer/database/project_db/pjt_seal.py

SQL calls in this module (AST count): 4.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTSeal.terminal_id`: no cache guard found (queries on every read).
- `PJTSeal.cavity_id`: no cache guard found (queries on every read).


Status: static read of the code only. Nothing here has been profiled.
