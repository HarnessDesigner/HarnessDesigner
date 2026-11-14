# harness_designer/gl/arena_pool.py

GL-free bookkeeping and planning for the pooled arenas (free lists, tiers, the `plan` that decides which models go in which arena). Runs at idle time, once per burst of changes (`arena_buffer.ArenaPoolBase`), never per frame.

## Line 64-213 (`ArenaMap`), 125-145 (`free`), 185-204 (`slide`) — sorted free list on every release
`free` re-sorts the free ranges to merge neighbours and `slide` sorts the allocations by start. Both are O(n log n) in the number of allocations or free ranges in one arena (hundreds to low thousands). Released in bulk (a project close) that is O(k n log n); acceptable because it is a rare event, and it could use `bisect.insort` to keep the list ordered if closing a large project is ever slow.

## Line 216-404 (`_Planner`, `_drain_one`, `_drain`, `run`) — plan works on copies
The planner clones every arena (`ArenaMap.clone`) and plays moves on the copies, with nested loops over arenas and models and a sort per drain step. Cost is O(models x arenas) per pass, thousands of operations in the worst case, each cheap. Each pass allocates copies of every allocation table; memory is a transient few KB per arena. Fine for an idle-time task; do not call `plan` per frame.
