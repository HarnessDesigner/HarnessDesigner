# performance_notes/gl

Performance notes for `harness_designer/gl/`. Every module in `gl/` now has a note at the mirrored path (for example `gl/canvas_3d/axis_overlay.py` → `performance_notes/gl/canvas_3d/axis_overlay.md`).

## Highest-cost items

- `canvas_3d/axis_overlay.md` — the axis overlay rebuilds its whole mesh on every mouse move during a corner-grip resize.
- `canvas_base/camera_base.md` — `set_view` rebuilds the view matrix, its inverse and the frustum on every frame in the 3D canvas.
- `canvas_base/scene_light.md` and `canvas_3d/headlight.md` — per-frame NumPy arrays and uniform writes.
- `materials/material.md` and `vbo.md` — the `float(str(v))` round-trip on the draw path.
- `model_preview/canvas.md` and `canvas_3d/axis_overlay.md` — the legacy fixed-function pipeline, rebuilt per frame.

## Known issues flagged in these notes (not fixed)

- `canvas_base/canvas_window_base.md` — `CanvasWindowBase.__init__` unpacks `size` and crashes if the peg-board window's default `None` is used.
- `canvas_base/key_handler.md` — one daemon thread per canvas is never stopped.
- `canvas_3d/headlight.md` — `__update` divides by zero when the camera sits on its focal point.
- `canvas_base/key_handler.md` — `event_type is _events.EVT_GL_KEY_DOWN` is an identity check on strings.
- `canvas_3d/axis_overlay.md` — `GLOverlay.size` shadows `QWidget.size()`.
- `canvas_schematic/floor.md` — duplicates `canvas_pegboard/floor.py` line for line.
- `canvas_schematic/canvas.md` — `_debug_frame_end` only feeds commented-out code.
- `canvas_base/camera_base.md` — absolute import `from harness_designer import app`, unlike its neighbours.
- `info.md` — `get()` returns `None` on the first call despite its docstring.
