# harness_designer/database/project_db/pjt_wire.py

SQL calls in this module (AST count): 13.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTWire.terminals`: no cache guard found (queries on every read).
- `PJTWire.wire_markers`: no cache guard found (queries on every read).
- `PJTWire.layer_view_position_id`: cached after first read.
- `PJTWire.layer_id`: cached after first read.
- `PJTWire.is_filler_wire`: cached after first read.
- `PJTWire.circuit_id`: cached after first read.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `delete_layouts_at`.


Status: static read of the code only. Nothing here has been profiled.
