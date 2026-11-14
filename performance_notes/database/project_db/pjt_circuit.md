# harness_designer/database/project_db/pjt_circuit.py

Circuit rows, the member walk and the control panel. All reads come from the in-memory `TableData`; nothing here is SQL on a hot path. The costs are the Python walks.

## Line 224-275 (`PJTCircuitsTable.connected_members`) — reads every junction and wire in the project on each call
It runs five `select`s that return every row of terminals, splices, wire service loops, cable conductors and wires (a list of tuples each), builds the port maps for all of them, then walks from one member (`_walk_circuit`, line 308). O(project size) per call whatever the size of the chain. It runs once per circuit change (`propagate`, line 278, called by the four `circuit_id` setters when the value changes; once more by `add_member` and `merge_from`). `propagation_paused` (line 210) keeps a bulk move from walking once per member. User-action frequency, not per frame. If a very large project makes it noticeable, keep the port maps current instead of rebuilding (memory: one dict entry per junction, small) or walk outward through an index of points to owners.

## Line 187-204 (`members_changed`), 580-621 (`invalidate_members`, `_load_terminal_ids`)
`PJTCircuit` caches its member lists; `members_changed` invalidates the cache of the named circuits only, which is the right granularity.

## Line 308-438 (`_walk_circuit`, `_parallel_wires`) — breadth-first walks with `in` tests on lists
Both have three nested loops with membership checks (`in_loop` flagged). The chain sizes are tens of members, so this is fine; if a circuit with hundreds of members shows up, check whether the `in` tests are on lists and switch them to sets.

## Line 539-564 (`resistance`), 814-866 (`_trace_full`), 959-987 (`_prepare_solve`)
Each `PJTCircuit` property that re-traces the circuit does a full walk. `circuit_map`, `get_circuit` and `_trace_full` are read when the circuit dock refreshes (it builds its rows on a worker thread). Not per frame. See [circuit_solver.md](circuit_solver.md) for the solve.

## Line 1567-1803 (`PJTCircuitControl._confirm_move`, `set_obj`)
UI population; runs on selection change, with a sort. Not a concern.
