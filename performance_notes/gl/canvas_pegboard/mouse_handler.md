# harness_designer/gl/canvas_pegboard/mouse_handler.py

## Line 19-20 (`MouseHandler._get_view_object`) — one attribute read per call
Returns `obj.objpegboard`. Same as the 3D version: one attribute lookup per call, nothing to gain.
