# harness_designer/gl/canvas_3d/axis_overlay.py

## Line 300-460 (`GLOverlay._on_mouse_motion`) — full model rebuild on every resize-drag event
Lines 438-440: when a corner grip is held (`grab_location` 1 to 4), every mouse-move event calls `self.build_model(max(w, h))` and then `self.set_angle(...)`. `build_model` (see below) regenerates three cylinders and a sphere, recomputes normals for all four, and creates four new `Plastic` material objects. That runs on the UI thread on every motion event for the whole drag. This is the largest cost in the file. A resize drag should only update the size, and rebuild the mesh on mouse release (or throttle it to, say, once per frame).

The move grip (`grab_location` 5) does not rebuild and is cheap.

## Line 462-527 (`GLOverlay.build_model`) — geometry, normals and materials built from scratch
Creates four meshes and four materials, computes normals through `_utils.compute_normals`, and rotates the arrays with `@=`. The nested `_unpack` function is redefined on every call. Called once at construction, and again on every resize drag event (see above). The geometry depends only on the size, so it could be cached per size, and the materials could be created once in `__init__`.

## Line 529-560 (`GLOverlay.set_angle`) — called every frame
`CanvasBase`'s canvas-3d `_on_draw` calls `axis_overlay.set_angle(...)` every frame (see `canvas_3d/canvas.md`). Each call builds two `Point`s, calls `update()`, and the camera-eye computation is a few small NumPy operations. Calling `update()` every frame keeps the overlay repainting in step with the main view. Not expensive, but the overlay repaints every frame even when the camera has not moved.

## Line 603-607 (`initializeGL`) and 624-688 (`paintGL`) — legacy fixed-function pipeline, per frame
`paintGL` runs the whole fixed-function sequence on every paint: `glPushMatrix`, `gluLookAt`, `glVertexPointer`/`glNormalPointer` with client arrays, and four `glMaterialfv` calls per mesh, four meshes per frame. The camera's "up" is recomputed with `float(str(v))` on line 664, the same string round-trip seen in other files. The lookat is recomputed every frame even though the camera only moves on a drag. This pipeline is the old one; `canvas_3d` uses shaders, so this widget is the only fixed-function one in the 3D view. See `model_preview/canvas.md` for the same concern.

## Line 139-147 (`Overlay.set_angle`) and 149-160 (`SetSize`) — thin forwards
No concerns.

## Line 103-136 (`resizeEvent`, `moveEvent`) — a `QTimer.singleShot` per event
Each resize or move creates a single-shot timer to write the new size or position into config. A drag produces many move events, so many timers are created. The writes are cheap; the timer churn is minor. Writing directly would also work, but the deferral may be intentional (see the comments in `canvas_window.py`).

## Line 39-89 (`Overlay.__init__`) — deferred positioning
Uses `CallAfterStart` to move the overlay once the parent has a real size, then shows it. The nested `_do` is defined only when the saved position is missing. No performance concerns.

**Functional issue (flagged, not fixed):** `GLOverlay.__init__` sets `self.size = None` (line 184) and `resizeGL` sets `self.size = (width, height)` (line 621). Both shadow the inherited `QWidget.size()` method on this instance. Nothing in this file calls `gl_overlay.size()` today, so there is no crash, but any Python caller that does will get a tuple or `None` instead of a `QSize`. Renaming the attribute (for example to `self._gl_size`) would remove the shadowing.

**Typing:** `GLOverlay.__init__(size: tuple[int, int] = (-1, -1))` is fine. `resizeGL` and `Overlay.SetSize` are typed; `build_model` stores its result on `self._triangles` and returns nothing. It was annotated `-> tuple[np.ndarray, np.ndarray, np.ndarray]` by an earlier spec pass, which was wrong; changed to `-> None` in this pass.
