# harness_designer/geometry/slot_pool.py

How it all works: the module docstring of `database/project_db/pjt_housing.py` ("POOLED 3D STORAGE", sections 3 and 4); this note is only the cost.

Pre-allocated chunked storage for `Point` / `Quaternion` / `Angle` data (design in the module docstring). Built 2026-11-14; the allocator was checked with 6,000 random allocations and releases against a brute-force model (no overlapping blocks, free runs always merged and sorted, best fit confirmed, rows reset on release).

## Cost of the operations
`allocate` scans every free run of every chunk (tens of runs): microseconds, and it runs once per housing. `release` loops over the block's slots to evict live members and resets the rows (about 600 slots for a 100-cavity housing): well under a millisecond, once per deleted housing. `register` is one weakref and a dict-free list write per `Point` / `Angle` built, once per object. `members(block)` builds a list of one dereference per slot: about 30 us for 700 slots, called once per cascade frame. `array` and `row` are plain slices (7 us for the 300 angles of a 100-cavity housing). Each call takes an `RLock`; the lock is uncontended in practice (the circuit dock reads rows from a worker thread, nothing else).

## Memory
A chunk is allocated at full size: 7,070 point slots x 12 bytes (85 KB) and 3,070 angle slots x 64 bytes (196 KB), about 281 KB for the pair, which holds 10 housings of 100 cavities or about 90 housings of 10 cavities. Unused slots are not wasted work (they hold neutral values and are rotated with the block) but they are memory: a project with one small housing still holds a whole chunk (281 KB). Empty chunks are never freed (nothing may move), so the pool's size is its peak. A `Point` or `Angle` over a view is still an ndarray object of about 100 bytes, the same as one with its own array, so pooling does not change the per-object cost.

## Possible improvement, not worth it yet
Freeing a chunk that has become completely empty would return memory after a big project is closed, but `reset()` already drops everything when a project is loaded and the sizes are small.
