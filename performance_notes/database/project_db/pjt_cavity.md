# harness_designer/database/project_db/pjt_cavity.py

SQL calls in this module (AST count): 41.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTCavity.aabb`: cached after first read.
- `PJTCavity.obb`: cached after first read.
- `PJTCavity.terminal`: cached after first read.
- `PJTCavity.terminal_position3d_id`: cached after first read.
- `PJTCavity.wire_position3d_id`: cached after first read.
- `PJTCavity.wire_position3d_id_raw`: cached after first read.
- `PJTCavity.terminal_position_pegboard_id`: cached after first read.
- `PJTCavity.wire_position_pegboard_id`: cached after first read.
- `PJTCavity.wire_position_pegboard_id_raw`: cached after first read.
- `PJTCavity.seal`: cached after first read.
- `PJTCavity.angle3d`: no cache guard found (queries on every read).


Status: static read of the code only. Nothing here has been profiled.
