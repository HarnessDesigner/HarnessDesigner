# harness_designer/database/project_db/pjt_wire_layout.py

SQL calls in this module (AST count): 7.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTWireLayout.position3d_id`: cached after first read.
- `PJTWireLayout.position2d_id`: cached after first read.
- `PJTWireLayout.position_pegboard_id`: cached after first read.
- `PJTWireLayout.attached_wires`: no cache guard found (queries on every read).


Status: static read of the code only. Nothing here has been profiled.
