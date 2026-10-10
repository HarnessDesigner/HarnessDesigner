# harness_designer/gl/canvas_schematic/canvas.py

## Line 101-128 (`Canvas.add_object`) — linear membership test before every add
`if obj in self._objects` (line 116) is a linear scan when `_objects` is a list. Loading a project adds every schematic object, so the total cost is quadratic in the number of objects. A set (or a dict keyed by identity) would make the check constant time. Worth changing if project loads with many objects are slow.

Also `self.Refresh()` on line 128 runs once per added object. The comment says it is needed for repaint after load. It is cheap while inside a `with canvas:` batch, and calling it per object outside a batch causes one repaint request per object.

## Line 130-140 (`add_preview_object`) — same linear membership test
Runs once per wire drawn during placement. Same `in` check as above; cost is small because a preview is a single object.

## Line 142-156 (`light_position`) — allocation per read
Same as the pegboard `light_position`: builds a new NumPy array per read.

## Line 166-241 (`Canvas._set_view`) — rebuilds only when the camera is dirty
Same pattern as the pegboard canvas. The projection is built element-wise and only when the camera changes.

## Class attributes line 55 (`_debug_frame_end = True`)
Marked as a temporary debug flag in the source (`# DEBUG (temporary)`). In `canvas_base.py` the only references to `_debug_frame_end` are inside commented-out code (lines 1242 and 1268), so setting it has no effect today. Either remove the flag or re-enable the code it was meant to control.

**Typing:** `size: QtCore.QSize = None` changed to `QtCore.QSize | None = None` in this pass.
