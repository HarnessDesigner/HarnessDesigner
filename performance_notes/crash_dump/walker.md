# harness_designer/crash_dump/walker.py

Walks an object graph from one or more roots (breadth-first over an explicit queue, not recursion, so a cycle or a shared object reached from two places is handled the same way: once an id has been seen, every further encounter just emits a ref, never re-queued or re-walked), producing one node dict per captured object for the writer to serialize.

Nested loops (cost grows with the product of the sizes; check the sizes are small): `_build_node` (lines 85-117, depth 2).

Status: static read of the code only. Nothing here has been profiled.
