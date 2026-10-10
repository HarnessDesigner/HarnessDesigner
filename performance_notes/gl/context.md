# harness_designer/gl/context.py

## Line 86-103 (`GLContext._acquire`) — two Qt calls on every acquire
Every `with ctx:` calls `QOpenGLContext.currentContext()` and `QOpenGLWidget.context(canvas)` before deciding whether to call `makeCurrent()`. A single paint can enter this context several times (`_on_draw` and the helpers it calls). Each entry does two Qt queries and a lock acquire. The cost is small per call, but it adds up across a frame's many `with self.canvas.context:` blocks (see `floor.py` `render`, `scene_light.py` `render`, `headlight.py` `set`).

Re-entrancy is needed for correctness (the docstring explains why), so the lock stays. The two Qt queries could be skipped when `ref > 0` on the same thread, but the code deliberately re-checks on every acquire because another widget can steal the current context. That trade-off is intentional; not changed.

## Line 105-118 (`GLContext._release`) — cheap
Decrements the count and calls `doneCurrent()` only at the outermost exit, when this context made current. No performance concerns.
