# harness_designer/gl/wire_pool.py

Wire paths as rows of a texture buffer (5 RGBA32F texels per piece, 20 floats). One draw per conductor, and `wire_batch.py` merges those into one draw per arena.

## Line 126-150 (`WirePool.pack`) — vectorised, called when a wire's path changes
Builds a `(pieces, 20)` float32 array with column assignments and one `cumsum`; no Python loop over pieces. It runs when a wire's rows are (re)written, not per frame, and is the right shape. Cost is a few tens of microseconds for a typical wire.

## Line 61-103 (`WireArena`), 106-310 (`WirePool`) — one texture buffer per arena
`upload` writes a wire's rows with `glBufferSubData`; the texture buffer is rebound when the buffer is replaced (`_buffer_replaced`). Rows hold each piece's first vertex relative to the wire, so moving a wire is a copy of its rows. Measured by the author (MEMORY.md): rewriting a wire's rows in place takes about 8 us.

## Line 283-291 (`_desired_tiers`)
Every wire is short tier (no tiering for wires), so this loops over all keys of every arena on each maintenance check. O(wires) per check; the check runs once per burst of changes, so fine.

## Memory
80 bytes per piece (20 floats). A wire of 50 pieces is 4 KB; 1,000 wires of 50 pieces is 4 MB. Small next to the model arenas. Arena capacity is reserved up front, so VRAM use is the capacity, not the live rows (same trade as the model pool).
