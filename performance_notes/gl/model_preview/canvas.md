# harness_designer/gl/model_preview/canvas.py

## Line 33-68 (`_calculate_obb`) — Python loops for the corner list
Builds the eight OBB corners with a triple nested Python loop and `np.array` on each. Runs once per `set_model` (a model load), not per frame. Fine at this size; vectorising would be cleaner but not needed.

## Line 72-89 and 93-114 (`_find_best_corner_view`, `_calculate_camera_distance`) — small per-load helpers
Run once per `set_model`. No concerns.

## Line 158-183 (`set_model`) — computes the OBB and smooth normals on each model load
`_calculate_obb`, `_find_best_corner_view` and `_utils.compute_smooth_normals` all run on the vertex data. For a large model this is the expensive part of the preview, and it runs once per load. Expected.

## Line 214-219 (`resizeGL`) and 221-231 (`paintGL`) — per-frame, and gated by `isVisible()`
`paintGL` returns early when the widget is hidden, which avoids drawing an invisible preview. Good.

## Line 237-273 (`setup_projection`) — rebuilt every frame with legacy calls
Every paint runs `glMatrixMode`, `glLoadIdentity`, `gluPerspective`, `glMatrixMode`, `glLoadIdentity`, and `gluLookAt`. These are fixed-function calls. The rest of `gl/` builds its matrices in NumPy and uploads them as shader uniforms, so this widget uses a different, older pipeline than the others. Two things follow:
- The matrices are recomputed every frame even though `set_model` is the only thing that changes the camera. Caching the projection and the view until the model or the widget size changes would remove the per-frame work.
- Mixing the fixed-function pipeline with a core-profile context can fail on some drivers. Not verified here.

**Functional issue (flagged, not fixed):** `render_model` (line 290) calls `glEnableVertexAttribArray(1)` and sets pointers for attributes 0 and 1, but only enables attribute 1. Attribute 0 is never enabled, and line 293 disables attribute 0 at the end. Whether this renders correctly depends on what state the context is left in. Needs a run to confirm.

**Typing:** `_calculate_obb` and friends have UNKNOWN docstrings left from the generated template. The annotations are correct; the docstrings should be filled in.
