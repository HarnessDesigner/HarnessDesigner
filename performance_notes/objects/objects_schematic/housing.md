# harness_designer/objects/objects_schematic/housing.py

## Line 288-343 (`Housing.render`) — two full inherited render passes per frame, plus per-frame attribute swapping
`render` calls `super().render(shaders)` once for the body (line 315) and once for the corner label (line 339). Each `super().render` is the full `BaseVar.render` pipeline, so the housing pays two complete render passes, each with its own `with shaders.*:` blocks, material upload, and bounds `mark_visible` calls. Between them it swaps six attributes on and off (lines 317-343). The label is drawn through the same pipeline as the body by design; the cost is the duplicated pipeline overhead per housing per frame. With many housings on screen this doubles the per-object overhead for the whole view.

The swaps themselves are cheap (attribute assignment). `_is_180(real_angle.y)` (line 331) is evaluated every frame as well, which is trivial on its own.

## Line 306-313 — leftover DEBUG block in the render path
The render method carries a commented `print` with a "DEBUG (temporary)" note referencing `self._aabb_manager._tags`. It is commented out, so it costs nothing at runtime, but it is dead code inside a per-frame method. Flagged for removal, not removed here.

## Line 192-264 (`_compute_obb`, `_compute_aabb`, `_update_position`, `_update_angle`) — bounds recompute on every move and rotation
Each mouse-move or angle event recomputes bounds for the housing; the terminals and cavities that cascade from it recompute their own (see `terminal.md` and `cavity.md`). Same shape as the 3D housing, and the same caching point applies.

## Line 265-285 (`_build_corner_label`) — rebuilds the label `Text` on every name, angle, or position change
`_text.Text(...)` is constructed each time (line 279), which means a new text layout and texture build for every change. That is correct when the text changes, but `_update_angle` (line 259) also calls it, so a pure rotation rebuilds the glyph layout even though only the angle changed. Caching the `Text` and changing only its angle would avoid the rebuild on rotation.
