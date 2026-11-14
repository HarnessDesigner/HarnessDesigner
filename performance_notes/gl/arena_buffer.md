# harness_designer/gl/arena_buffer.py

The GPU half of the pooled arenas (models in `vbo.py`, wire paths in `wire_pool.py`) and the idle-time maintenance both pools share. Nothing here runs per frame; it runs when models or wires are added, removed or promoted, and once per burst of changes.

## Line 243-277 (`ArenaPoolBase._maintenance_wanted`), 281-308 (`_request_maintenance`) — a cheap check, then one deferred pass
`_request_maintenance` returns at once if a pass is already pending, hops to the main thread if called from another, runs `_maintenance_wanted` (a loop over the arenas, O(arenas), arenas are few) and only then schedules one `CallLater`. So a burst of 1,000 model releases costs one check and one pass. That is the right shape. Keep `_maintenance_wanted` cheap; it runs on every release and promotion.

## Line 112-136 (`BufferArena._rebuild`) — compaction copies GPU to GPU
`slide` plans the moves, a fresh buffer is created at the new capacity, each live range is copied with `glCopyBufferSubData` (one call per move), and the old buffer is deleted. No CPU round trip. The temporary cost is the old and the new buffer being alive together, so VRAM peaks at old + new for a moment: with the long arena at 144 MB that is up to about 290 MB in transient VRAM during a compaction of a full long arena. That is the price of a copy that never leaves the GPU; trimming only when an arena is mostly empty (`should_compact` with `_compact_min_free`) keeps it rare. Worth knowing if VRAM is tight on a small GPU.

## Line 347-378 (`_execute`) — replays the plan and logs
Replays each planned op on real buffers, with an f-string per op for the log. Per pass, not per frame.

## Memory
A pooled design wastes VRAM in two places (see `gl/vbo.md`): the open long arena reserves its full capacity even when nearly empty, and compaction needs the transient double buffer above. In exchange there are far fewer buffers and VAOs, and fewer state changes per frame.
