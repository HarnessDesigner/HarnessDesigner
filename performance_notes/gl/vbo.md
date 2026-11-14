# harness_designer/gl/vbo.py

Per-draw cost of the model path and the pooled arenas. Pooling (2026-11-08, `arena_pool.py` / `arena_buffer.py`) is built and in use; the old per-model-buffer description no longer applies.

## Line 493-538 (`VBOHandlerBase.render`) — string round trip and three uniform writes per draw
- Line 528 builds the rotation uniform as `[float(str(v)) for v in angle.as_quat_numpy.tolist()]`: four float -> string -> float conversions per draw. `as_quat_numpy` is already a float array, so the uniform can take `.tolist()` directly. Measured cost of the same conversion pattern in `Point.x`: about 0.4 us per value, so about 2 us per draw; at 1,000 draws a frame, 2 ms.
- Lines 527 and 529 write `position` and `scale` with `position.as_float` and `scale.as_float`, each a list comprehension of `float(str())` (2.1 us each, measured in `geometry/point.md`). That is about 4 us more per draw, 4 ms at 1,000 draws. Using `as_numpy` (a view, 0.06 us) and passing it to the uniform setter would remove it.
- The three `glUniform` writes happen on every draw even when the same mesh draws repeatedly with the same transform. A last-written cache per program would skip identical writes (a few floats of memory per program). The `normal_mode` probe is now a class flag (`program.has_normal_mode`), as intended.
- One VAO bind, one `glDrawArrays`, one unbind per call is the expected cost of an unbatched draw. The only larger gain is batching meshes that share a program, which the wire path already does (`wire_batch.py`).

## `render_raw` (2026-11-14) -- the same draw from plain floats, over a range of the mesh
`VBOHandlerBase.render_raw(program, position, rotation, scale, smooth, first, count)` skips the `Point` / `Angle` objects and the `float(str(v))` round trips above: the caller passes a tuple of 3 floats, a list of 4 and a tuple of 3. The rotation rings use it (38 draws a ring, about 18 us each including the caller's loop, against about 30 us through `render`, measured: `rotation_handlers/rotation_ring/_protractor_base.md`), and `first` / `count` let one mesh hold many parts that are drawn separately (the hovered tick). The items above still apply to `render`, which every other object uses.

## Line 320-327 (`_compute_local_obb`)
Two `Point(*[float(str(item)) ...])` constructions per model, once per VBO creation. Not per frame.

## Line 703-1103 (`PooledVBOHandler`) — VRAM cost of tiers
Two arena tiers: one open long arena reserves `MODEL_ARENA_CAPACITY_VERTICES` (4,000,000 vertices, 144 MB) and short arenas are half that. The long arena reserves its full size even when it holds one model, so VRAM can go UP right after the first promotion (still open item 1 in MEMORY.md: arena sizes are not tuned). Trade: far fewer buffers and VAOs; cost: reserved but unused VRAM. Pick the sizes from the real mesh-size distribution (the housing models in `D:\...\models`), not from guesswork.

## Line 868-921 (`update`)
`glBufferSubData` for one model's vertices into its arena slot; once per model change, not per frame.
