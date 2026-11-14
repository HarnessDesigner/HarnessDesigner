# harness_designer/pegboard_print/renderer.py

render_tile(canvas, left, top, width_px, height_px, mm_per_pixel) and content_bounds(canvas). Renders by pointing the pegboard canvas's own camera at the tile (camera.CenterOn + camera.distance = mm_per_pixel * 1000, because that camera's scale is distance / 1000 mm per pixel), setting canvas.size, and calling canvas._on_draw() into a multisampled QOpenGLFramebufferObject.

Cold path (214 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
