# harness_designer/objects/cable.py

The cable facade (a jacketed or ribbon cable with its conductors, split ends and shield sleeves). 56 methods; most are user-action frequency (split, join, add sleeve, fan out). Per drag, `follow_drag` and the lead walkers run on every move.

## Line 473-503 (`follow_drag`) — per move, only for a split end
For each split end: sync the split points, then move the free leads by the end's displacement (`_carry_free_leads`). Cost is O(conductors) point moves (each 20-70 us with `Point +=`, see `geometry/point.md`), so a cable of 24 conductors is about a millisecond per move per split end in the interpreter. Fine for typical cables; scales linearly.

## Line 192-284 (`lead_wires`, `conductor_wires`, `lead_chain`) — walks per conductor
`conductor_wires` loops conductors and, for each, calls `leads_of` (an indexed select on `cable_conductor_id`) and tests `wire not in result` on a list (O(n^2) in the number of leads). `lead_chain` follows a lead through splices and service loops with a `while True` walk. These run per user action and per drag start; for a 100-conductor cable the `not in result` list test is the first thing to turn into a set (no memory concern).

## Line 1511-1550 (`delete`), 682-901 (`split_end`, `join_end`)
Multi-row writes (deleting or creating the leads and markers); user-action frequency, inside a gesture so one transaction. Not a concern.
