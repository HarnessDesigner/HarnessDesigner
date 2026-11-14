# harness_designer/drag_handlers/editor_3d/cable.py

## Line 66-74 (`Cable.__call__`) — two array copies, then the wire drag, then conductor follow
Each move copies the start and stop positions (`np.array(..., dtype=np.float64)`, two 3-element arrays), runs the wire drag's `__call__` (see [wire.md](wire.md)) and then `target.follow_drag('3d', before_start, before_stop)`, which moves the conductors' free ends by the same delta. The copies are tiny. The conductor follow is O(conductors), each a `Point` move at 20-70 us, so a 24-conductor cable adds on the order of a millisecond per move in the interpreter. Not a concern for typical cable sizes; it grows linearly with conductor count.
No snap probe set is built (a cable's ends are free), so it is cheaper per move than a wire drag.
