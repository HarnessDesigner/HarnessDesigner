# harness_designer/database/project_db/pjt_wire_path.py

SQL calls in this module (AST count): 18.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTWirePath.wire_id`: cached after first read.
- `PJTWirePath.idx`: cached after first read.
- `PJTWirePath.point3d_id`: cached after first read.
- `PJTWirePath.point_pegboard_id`: cached after first read.
- `PJTWirePath.point2d_id`: cached after first read.
- `PJTWirePath.bundle_id`: cached after first read.
- `PJTWirePath.concentric_id`: cached after first read.
- `PJTWirePath.transition_id`: cached after first read.
- `PJTWirePath.transition_branch_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
