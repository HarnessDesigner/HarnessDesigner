# harness_designer/database/project_db/pjt_point_pegboard.py

SQL calls in this module (AST count): 29.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTPointPegboard.x`: cached after first read.
- `PJTPointPegboard.y`: cached after first read.
- `PJTPointPegboard.z`: cached after first read.
- `PJTPointPegboard.parent_point_id`: cached after first read.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTPointPegboard.is_referenced`.


Status: static read of the code only. Nothing here has been profiled.
