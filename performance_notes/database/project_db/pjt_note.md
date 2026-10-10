# harness_designer/database/project_db/pjt_note.py

SQL calls in this module (AST count): 12.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTNote.size`: cached after first read.
- `PJTNote.h_align`: cached after first read.
- `PJTNote.style`: cached after first read.
- `PJTNote.position2d_id`: cached after first read.
- `PJTNote.position3d_id`: cached after first read.
- `PJTNote.position_pegboard_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
