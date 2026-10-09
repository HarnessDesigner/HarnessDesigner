# harness_designer/gl/canvas_pegboard/camera.py

## objects_in_view - removed
The camera scan is gone. Its callers now read the canvas's own bounds pool, which is filled and reset once per frame, so nothing recomputes a scene scan per access:
- objects/objects_pegboard/base_pegboard.py show_table: self._aabb_manager.visible_objects()
- objects/objects_3d/wire_service_loop.py: self._aabb_manager.visible_objects(), mapped to view.parent
- ray_tracing/dialog.py: editor3d.editor.bounds_manager.aabb.visible_objects()
- gl/canvas_base/canvas_window_base.py objects_in_window: self._canvas.bounds_manager.aabb.visible_objects(), returning view.parent

## zoom_to_fit - still reads objpegboard bounds per object, no callers
Dead code, no per-frame cost.
