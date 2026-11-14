# harness_designer/gl/wire_batch.py

Collects every wire entry of a frame and draws them with one `glDrawArrays` per arena (`CanvasBase._flush_wire_batch`, `canvas_base.py` line 1091). Measured by the author (MEMORY.md, offscreen, 100 random wires, 5,000 pieces): whole pass 177 ms (per-piece draws) -> 8.6 ms (per-wire draws) -> 3.05 ms (one draw), CPU submit 0.23 ms.

## Line 250-283 (`WireBatch._draw_group`) — per arena, per frame
Stacks the entries into one array (`np.stack(entries)`), computes the vertex offsets with one `cumsum`, uploads them with `glBufferSubData`, binds two texture buffers and draws. Cost is O(conductors) per frame: the stack is one copy of `conductors x 10` texels (160 bytes per entry, `ENTRY_BYTES`), and the upload the same again. For 1,000 conductors that is about 160 KB per frame, small for the GPU, and about a millisecond of `np.stack` over 1,000 small arrays on the CPU. If it ever shows up, keep a persistent `(capacity, 40)` float32 array and have each wire write its row in place (saves the per-frame stack; costs holding the array, a few hundred KB for a large project).

## Line 201-226 (`_entry_buffer`) — grows by 1.5x, never shrinks
A buffer and texture per arena slot, created on first need and reallocated with `glBufferData` when more entries arrive. The capacity only grows, so after a very large project closes it keeps its peak (160 bytes per entry; a 10,000-conductor peak is 1.6 MB, plus the texture buffer view of it). Not a concern.

## Line 187-198 (`_vao`)
One empty VAO per GL context, cached by `id(context)`. Fine. The dict keeps an entry per context ever seen (contexts are few).

## Line 48-79 (`make_entry`)
Builds one 40-float32 entry (160 bytes) per conductor. It is not per frame: `TubeMixin._batch_wire` caches the entries on the wire and rebuilds them only when the pool stamp, look, selection, material or bare-end state change (see `objects/mixins/tube.md`); every other frame it just calls `BATCH.add` with the cached entry.
