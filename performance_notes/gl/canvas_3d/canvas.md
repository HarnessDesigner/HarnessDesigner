# harness_designer/gl/canvas_3d/canvas.py

## Line 37-65 (`_build_perspective_matrix`) — a 4x4 NumPy matrix built on every frame
Called from `_set_view` (line 251) on every frame. It allocates a 4x4 float32 array and sets five elements. Small, but it runs every frame. The matrix only changes when the window's aspect ratio or the far plane changes, so it could be cached and rebuilt on resize.

## Line 230-255 (`Canvas._set_view`) — per-frame GL state and matrix setup
Each frame it:
- enables depth test and program point size, sets the line width, and clears the colour and depth buffers (lines 241-245);
- builds the projection matrix (above) and a look-at matrix (`build_lookat_matrix`, line 252);
- hands both to `camera.set_view`.

The GL enables and the line width are the same every frame. They are cheap, but they could be set once in `initializeGL`, provided nothing else changes that state between frames. Not verified; the base class may reset state. The look-at matrix is rebuilt from camera position each frame, which is required while the camera moves.

## Line 269-291 (`Canvas._on_draw`) — per-frame draw sequence
Every frame it runs headlight uniforms, the focal-target render, and the axis overlay update. The overlay update computes `(camera.position - camera.focal_position).inverse` each frame (line 291). That is one `Point` subtraction and an inverse per frame even when the camera has not moved. A cache keyed on the camera's position and focal point would skip it.

`_on_draw` also has a bare `except Exception` around the headlight and focal target calls that logs and continues, so an error in those draws is logged each frame rather than stopping the frame. That is intentional but noisy if a persistent error occurs.

## Line 154-162 (`_on_camera_moved_for_notes`) — batch update on every camera move
Bound to `camera.position`. Runs `_text.update_camera_tracking` once per camera move (not once per note), as the comment says. Cost depends on the number of tracked notes. Fine.

## Line 194-210 (`delete_focal_target`) — intentionally clears the reference first
Sets `_focal_target` to None before deleting it so nothing draws a half-deleted target. No performance concern.

**Typing:** `size: QtCore.QSize = None` on line 87 was changed to `QtCore.QSize | None = None` in this pass.
