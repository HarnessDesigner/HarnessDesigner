# harness_designer/gl/canvas_base/canvas_base.py

## Line 986-1080 (`_draw_scene`) — per-frame ctypes cast, per-object view lookup, and a list removal that can go quadratic
- Line 993 does `ctypes.cast(ref_address, ctypes.py_object).value` for every row of the frame's object data. That is a ctypes call per object per frame. The row could carry the Python object reference directly, or the cast could be cached per row when the row set is unchanged.
- Lines 997-1002 call `self._object_refs.remove(obj_ref)` for every dead object. `list.remove` is a linear scan, so removing k dead objects from n refs costs O(k*n) per frame. A set (or a dict keyed by the row) makes each removal constant time. The cost only shows up when many objects are deleted at once, but the scan repeats every frame until the dead rows are cleared.
- Line 1019 calls `self._get_view_object(obj)` for every visible object every frame. The view for a given object does not change, so the mapping can be cached on the facade or in a dict keyed by identity.
- Lines 1050-1080 render the selected and active-handler objects through the same full pipeline. That is one extra pass each, by design (see the selected-overlay docstring), so no change.

## Line 919-924 (`paintGL`) and 1162 (`_on_draw`) — paint entry point
`paintGL` only forwards to `_on_draw`, so the cost is entirely in `_draw_scene` and `_set_shader_programs` (below).

## Line 940-982 (`_set_shader_programs`) — every shader uniform rewritten every frame
Each frame binds `faces`, `edges`, `vertices`, and `texture` in turn and writes the projection and view matrices (plus `view_position`, `floor_y`, `has_reflection`, and `show_depth` on faces) whether or not the camera moved. Each write is a `glUniform*` call and each bind is a `with` block. Keeping the last-written matrices and skipping the writes when they are equal would remove most of this on a still frame, and the camera already knows when its matrices change.
