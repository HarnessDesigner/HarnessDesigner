# harness_designer/handlers/wire_circuit.py

Runs once when a wire is connected (called from the add-wire handlers and `wire_snap.commit_snap`). User-action frequency, not per frame.

## Line 44-120 (`_reconcile_circuits`) — one `connected_members` call, which reads every junction and wire in the project
`circuits_table.connected_members(wire.db_obj)` (line 84) builds port maps from every terminal, splice, service loop, cable conductor and wire row of the project and then walks from the wire (see `database/project_db/pjt_circuit.md`): O(project size) per connected wire. For one click that is milliseconds even in a large project. A bulk operation that connects many wires in a loop (importing or duplicating a harness) pays it per wire; if that case exists, wrap the loop in `propagation_paused()` and reconcile once at the end.

## Line 124-192 (`_replicate_operating_temp`)
Loops over the circuit's members with an f-string per member for the log and `in` tests on lists. Members number in the tens. Not a concern.
