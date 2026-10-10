# harness_designer/database/project_db/pjt_terminal.py

SQL calls in this module (AST count): 48.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTTerminal.is_start`: no cache guard found (queries on every read).
- `PJTTerminal.voltage_drop`: no cache guard found (queries on every read).
- `PJTTerminal.volts`: no cache guard found (queries on every read).
- `PJTTerminal.load`: no cache guard found (queries on every read).
- `PJTTerminal.cavity_id`: no cache guard found (queries on every read).
- `PJTTerminal.circuit_id`: no cache guard found (queries on every read).
- `PJTTerminal.seal`: no cache guard found (queries on every read).
- `PJTTerminal.position2d_id`: cached after first read.
- `PJTTerminal.wire_position3d_id`: no cache guard found (queries on every read).
- `PJTTerminal.wire_position3d_id_raw`: no cache guard found (queries on every read).
- `PJTTerminal.wire_position_pegboard_id`: no cache guard found (queries on every read).
- `PJTTerminal.wire_position_pegboard_id_raw`: no cache guard found (queries on every read).
- `PJTTerminal.wire_position2d_id`: no cache guard found (queries on every read).
- `PJTTerminal.wire_position2d_id_raw`: no cache guard found (queries on every read).
- `PJTTerminal.attach_position3d_id`: no cache guard found (queries on every read).
- `PJTTerminal.attach_position3d_id_raw`: no cache guard found (queries on every read).
- `PJTTerminal.attach_position_pegboard_id`: no cache guard found (queries on every read).
- `PJTTerminal.attach_position_pegboard_id_raw`: no cache guard found (queries on every read).
- `PJTTerminal.seal_position3d_id`: no cache guard found (queries on every read).
- `PJTTerminal.seal_position_pegboard_id`: no cache guard found (queries on every read).

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTTerminal.__check_for_other_starts`.
- `PJTTerminal.sync_free_wire_points`.

## Load-time functions
These run when the database is opened or built, not on every interaction.
- `PJTTerminal.load`.
- `PJTTerminal.load`.


Status: static read of the code only. Nothing here has been profiled.
