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

## `PJTCircuitsTable.connected_members` - reads every junction and wire in the project per call
`connected_members` builds the connection-point maps for ALL terminals, splices, wire service loops and wires (four `select`s over the project's cached tables), then walks from one member with `_walk_circuit`. That is O(project size) per call, whatever the size of the chain. It runs once per circuit change (`propagate`, called by the four `circuit_id` setters when the value changes, and once by `add_member` and `merge_from`), and once per connected wire in `_reconcile_circuits`, so it is user-action frequency, not per frame. `propagation_paused` stops a bulk move (`merge_from`) from walking once per member. If a very large project ever makes this noticeable, build the point maps once and keep them current, or walk from the member outward using an index of points to owners.
