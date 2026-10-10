# harness_designer/gl/canvas_pegboard/canvas.py

## Line 166-254 (`Canvas._set_view`) — rebuilds only when the camera is dirty
This is the good pattern: it returns early unless `camera.is_dirty`, so the projection is only rebuilt when the camera actually moves. The projection is a 4x4 NumPy array built element by element, once per camera move. Not on the per-frame path when the camera is still.

## Line 137-164 (`light_position` and `view_position`) — two identical properties
Both return `focal + np.array([300.0, 500.0, -300.0], dtype=np.float32)`. Each read allocates a new array and a new `Point.as_numpy`. If the renderer reads these per object per frame, that is one allocation per read; the result only changes when the focal point moves. Could be cached on focal-point change.

## Line 53-75 (`__init__`) and 78-88 (`set_draw_floor`) — construction and user-action paths
Nothing on the frame path. `set_draw_floor` calls `self._floor.set(...)` and `update()`.

## Line 102-110 (`resizeGL`) — updates `self.size` and viewport
Runs on window resize. `self.size = (width, height)` is set as a tuple, which `_set_view` reads. Fine.

**Typing/API:** `size: QtCore.QSize = None` changed to `QtCore.QSize | None = None` in this pass. `config: _config.Config.editor_pegboard = None` (line 54) is annotated without `| None` but defaults to `None`. Constructing the canvas without a config would fail in `super().__init__`. `CanvasWindow` always passes a config, so the default is never used. Flagged for review; signature not changed.
