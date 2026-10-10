# harness_designer/database/project_db/pjt_housing.py

SQL calls in this module (AST count): 63.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTHousing.cavities`: no cache guard found (queries on every read).
- `PJTHousing.wires`: no cache guard found (queries on every read).
- `PJTHousing.cover_position3d_id`: cached after first read.
- `PJTHousing.seal_position3d_id`: cached after first read.
- `PJTHousing.seal_position_pegboard_id`: cached after first read.
- `PJTHousing.boot_position3d_id`: cached after first read.
- `PJTHousing.tpa_lock_1_position3d_id`: cached after first read.
- `PJTHousing.tpa_lock_2_position3d_id`: cached after first read.
- `PJTHousing.cpa_lock_position3d_id`: cached after first read.
- `PJTHousing.seal`: no cache guard found (queries on every read).
- `PJTHousing.cpa_lock`: no cache guard found (queries on every read).
- `PJTHousing.tpa_lock1`: no cache guard found (queries on every read).
- `PJTHousing.tpa_lock2`: no cache guard found (queries on every read).
- `PJTHousing.tpa_locks`: no cache guard found (queries on every read).
- `PJTHousing.cover`: no cache guard found (queries on every read).
- `PJTHousing.boot`: no cache guard found (queries on every read).

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTHousing.wires`.


Status: static read of the code only. Nothing here has been profiled.
