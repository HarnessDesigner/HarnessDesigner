# harness_designer/objects/objects_pegboard/table.py

## Line 1494, 1504, 1572, 1605, 1626, 1652 (`_dispatch_hover`, `_clear_hover`, `_dispatch_press`, `_dispatch_double_click`, `_dispatch_release`, `_dispatch_drag_move`) and 1442 (`handle_wheel`) — the texture is regrabbed on every mouse event
Each of these ends with `self._regrab_texture()`. `_dispatch_hover` (line 1494) does so unconditionally on every mouse move that lands on the table, not only when the hovered target changes. `_regrab_texture` (line 538) calls `self._host.grab_rgba()` (line 592), which captures the whole hidden widget into an RGBA buffer, then re-uploads it with `glTexImage2D` (lines 600-602). The buffer is `width * height * 4` bytes on the CPU and the GPU upload is the same size. A table-sized widget is in the megabyte range, so a hover sweep across the table means a full capture and upload on every mouse-move event.

Fix options, in order of payoff:
1. Make `_dispatch_hover` regrab only when the hovered widget's own content changes (a cell highlight, a hover state visible in the capture). Pure pointer movement inside an unchanged cell needs no regrab.
2. Coalesce regrabs: mark the texture dirty in the event handlers and perform one capture per frame in `render` (the capture is already GL-context-guarded, so it runs at the right point).
3. Skip the `glTexImage2D` re-upload when `rgba` is byte-identical to the last one (a hash of the buffer is far cheaper than a full upload).

## Line 538-605 (`_regrab_texture`) — also writes `db_obj.size` on every capture that changes the size
Lines 625-630 write `self.db_obj.size` whenever `(world_w, world_h)` differs from the current scale. That is a database write, and it can happen on every capture during a resize. Coalescing the regrab (above) also coalesces this write.

## Line 509-517 (`_update_position`) — inherited GL-context update, then `_recompute_connector`, on every drag event
`super()._update_position` takes `with self.editor.context:` (see `objectsvar/base_var.md`), then `_recompute_connector()` runs on every drag event. The connector is a single cylinder, so its own cost is small; the context acquire is the same one described in `objects_3d/base_3d.md`.

## Line 637-720 (`render`) — up to three draws per frame, with state toggled around each
The quad (lines 700-716) toggles `glDepthFunc` to `GL_ALWAYS` and back, and binds and unbinds the texture every frame. `_render_connector` (line 720) then calls `super().render` through the full `BaseVar` pipeline (line 764) with the connector's own vbo/position/angle/scale/material swapped in and out (lines 737-768). `_render_selection_border` (line 680) is a third draw when selected. The connector swap is attribute assignment and cheap, but the full pipeline pass per frame is the same per-object overhead described in `objectsvar/base_var.md`.

## Line 723-768 (`_render_connector`) — cached geometry, swapped per frame
The connector's angle and scale are cached and only recomputed when an endpoint moves (module docstring). Good; no change needed beyond the pipeline cost above.
