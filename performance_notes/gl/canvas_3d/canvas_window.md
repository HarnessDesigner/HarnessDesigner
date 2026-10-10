# harness_designer/gl/canvas_3d/canvas_window.py

## Line 75-127 (`CanvasWindow._apply_fit`) — builds corner arrays on each fit
Creates an 8x3 corner array from a list comprehension, then runs three matrix products and a norm. Runs when the user fits the view (a user action, not per frame). Cheap.

## Line 130-139 (`resizeEvent`) and 141-197 (`_reposition_axis_overlay`) — runs on every resize event
Qt fires several resize events during a drag-resize. Each one repositions the axis overlay, with a few `pos()` and `size()` reads and a possible `move()`. The `isVisible()` guard already skips the layout-settling resizes at startup. Not a hot path.

**Typing:** `size: tuple[int, int]` (line 26) is a required parameter but `CanvasWindowBase` may accept `None`. Not changed here; the base class annotation decides. Left for the `canvas_base/canvas_window_base.py` review.
