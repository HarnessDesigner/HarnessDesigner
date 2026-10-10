# harness_designer/database/project_db/pjt_concentric_layer.py

SQL calls in this module (AST count): 11.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTConcentricLayer.wires`: no cache guard found (queries on every read).
- `PJTConcentricLayer.concentric_id`: cached after first read.
- `PJTConcentricLayer.idx`: cached after first read.
- `PJTConcentricLayer.num_wires`: cached after first read.
- `PJTConcentricLayer.num_fillers`: cached after first read.
- `PJTConcentricLayer.diameter`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
