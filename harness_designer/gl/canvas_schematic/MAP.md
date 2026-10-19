## FILES

#### __init__.py

`from . import canvas_window as _canvas_window` — package construction entry point, same pattern
`canvas_3d/`/`canvas_pegboard/` use. This is the landed, renamed home of what MEMORY.md's
"`new_canvas2d`" entries describe as an in-progress unification effort between the old `canvas2d`
(schematic) and `canvas_pegboard` directories — confirmed by directory layout and by
`canvas_base/camera_base.py` still containing a stray "new_canvas2d" comment (see that folder's
MAP.md) that the pegboard editor was NOT folded into this package; it stayed a sibling that shares
`canvas_base/` instead.

#### camera.py

`Camera(CameraBase)`, `is_top_down = True` — locked top-down orthographic 2D camera. Near-identical
twin of `canvas_pegboard.Camera` (same mechanics, same docstring); see that file's MAP.md entry.

#### canvas.py

`Canvas(CanvasBase)` — the schematic editor's GL surface. Per MEMORY.md's design note for this
unification, reuses the 3D view's own VBOs for *some* objects (same identity-transform technique
`canvas_pegboard/canvas.py` uses) but still creates its own new, simplified flat-primitive VBO
objects for others (e.g. corner-label text, cavity-slot rectangles) rather than reusing the real
3D part mesh everywhere — this is the one place schematic and pegboard rendering genuinely diverge
rather than just duplicate. `add_object()` calls `self.Refresh()` itself after registering an
object, unlike the 3D/pegboard canvases (whose repaint during load happens via their model's own
`_set_model()` callback) — schematic objects have no model-load step to piggyback on, so this
canvas needs the explicit repaint (see MEMORY.md "Stored project bounds" — "Schematic repaint
gotcha").

#### canvas_window.py

`CanvasWindow(CanvasWindowBase)` — thin wrapper, builds the inner `Canvas` then calls
`super().__init__()`. Adds one method `canvas_pegboard.CanvasWindow` does not have:
`add_preview_object(obj)`, forwarding to `Canvas.add_preview_object` — registers a wire that is
still being drawn (the interactive two-click wire-placement preview) with the canvas.

#### floor.py

`Floor(FloorBase)` — procedural top-down dot-grid floor, a single power-of-2 spacing tier (no
major/minor "nice value" pair — see `canvas_pegboard/floor.py`'s MAP.md entry for why that was
dropped). Confirmed byte-identical to `canvas_pegboard/floor.py` except for one line of module
docstring — see that file's entry for the still-open duplication this represents.

#### mouse_handler.py

`MouseHandler(MouseHandlerBase)` — the only override is `_get_view_object`, returning
`obj.objschematic`. Every other behavior (dispatch to `CanvasBase.active_handler_obj`, selection,
wheel easing) is inherited unchanged from the shared base, exactly as it is for the 3D and
pegboard editors.
