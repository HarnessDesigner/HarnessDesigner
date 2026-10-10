# harness_designer/gl/canvas_3d/mouse_handler.py

## Line 16-17 (`MouseHandler._get_view_object`) — one attribute read per call
A static method that returns `obj.obj3d`. It is called from the mouse dispatch path for each candidate object, so the cost is one attribute lookup per call. There is nothing to gain here.
