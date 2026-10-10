# harness_designer/database/project_db/pjt_circuit.py

SQL calls in this module (AST count): 37.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTCircuit.start_terminal`: no cache guard found (queries on every read).
- `PJTCircuit.load_terminals`: no cache guard found (queries on every read).
- `PJTCircuit.circuit_map`: no cache guard found (queries on every read).
- `PJTCircuit.circuit_num`: cached after first read.
- `PJTCircuit.description`: cached after first read.
- `PJTCircuit.wires`: no cache guard found (queries on every read).
- `PJTCircuit.wire_service_loops`: no cache guard found (queries on every read).
- `PJTCircuit.splices`: no cache guard found (queries on every read).
- `PJTCircuit.terminals`: no cache guard found (queries on every read).
- `PJTCircuit.housings`: no cache guard found (queries on every read).

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTCircuit.wires`.
- `PJTCircuit.wire_service_loops`.
- `PJTCircuit.splices`.
- `PJTCircuit.terminals`.
- `PJTCircuit.housings`.


Status: static read of the code only. Nothing here has been profiled.
