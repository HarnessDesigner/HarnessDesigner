# harness_designer/objects/objects_pegboard/chain_edges.py

## Line 42-100 (`touching_edges`) — rebuilds the chain's position list on every call
Each call rebuilds `ids`, `positions`, and the segment `distances` from the wire or bundle row, then searches `ids` with `.index`. The chain is short (start, a few waypoints, stop), and the function is called from `touching_budgets` once per drag arm (see `base_pegboard.md`) and from waypoint drag, so the cost is small. The `ids.index` lookup is linear in the chain length, which is fine for the chain sizes that occur here.
