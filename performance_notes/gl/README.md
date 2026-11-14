# performance_notes/gl

Performance notes for `harness_designer/gl/`. Every module in `gl/` has a note at the mirrored path. Refreshed 2026-11-13.

## Highest-cost items
- `vbo.md`, `materials/material.md` - per-draw `float(str(v))` conversions for position, rotation, scale and the emissive rim (about 6 us per draw, so milliseconds at a thousand draws a frame) and uniform writes that repeat when nothing changed.
- `canvas_base/canvas_base.md` - `_draw_scene` does a ctypes cast per object per frame, a list removal that can go quadratic when many objects die, a view lookup per object per frame, and `_set_shader_programs` rewrites every shader's matrices every frame.
- `canvas_base/camera_base.md` and `canvas_3d/canvas.md` - `set_view` rebuilds the view matrix, its inverse and the frustum on every 3D frame.
- `floor_outline.md` - the floor outline of a selected wire is recomputed in Python every frame (cache it; a few KB).
- `canvas_3d/axis_overlay.md`, `model_preview/canvas.md` - the legacy fixed-function pipeline, rebuilt per frame.

## Already good
The pooled model arenas and the wire pool with one batched draw per arena (`arena_buffer.md`, `arena_pool.md`, `wire_pool.md`, `wire_batch.md`; about 200 ms -> 3 ms per frame for 100 wires, measured by the author). The cost of that design is VRAM: the open long arena reserves its full 144 MB, and compaction needs a transient second buffer (`arena_buffer.md`, `vbo.md`).

## Known issues flagged in these notes (not fixed)
- `canvas_base/canvas_window_base.md` - `CanvasWindowBase.__init__` unpacks `size` and crashes if the peg-board window's default `None` is used.
- `canvas_base/key_handler.md` - one daemon thread per canvas is never stopped; an identity check on strings.
- `canvas_3d/headlight.md` - `__update` divides by zero when the camera sits on its focal point.
- `canvas_3d/axis_overlay.md` - `GLOverlay.size` shadows `QWidget.size()`.
- `canvas_schematic/floor.md` - duplicates `canvas_pegboard/floor.py` line for line.
- `info.md` - `get()` returns `None` on the first call despite its docstring.
