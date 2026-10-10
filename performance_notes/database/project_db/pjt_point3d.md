# harness_designer/database/project_db/pjt_point3d.py

SQL calls in this module (AST count): 25.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTPoint3D.x`: cached after first read.
- `PJTPoint3D.y`: cached after first read.
- `PJTPoint3D.z`: cached after first read.
- `PJTPoint3D.parent_point_id`: cached after first read.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTPoint3D.is_referenced`.


Status: static read of the code only. Nothing here has been profiled.
