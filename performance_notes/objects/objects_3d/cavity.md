# harness_designer/objects/objects_3d/cavity.py

## Line 142-160 (`Cavity.render`) — calls `super().render()` then draws up to two marker decals, every frame
`super().render(shaders)` runs the full `BaseVar.render` for the cavity's
placeholder geometry, which is usually invisible (see `identify`'s docstring).
That is a full render pass for an object with no visible mesh, every frame.
Checking `is_visible` before the super call would skip it, but the `BaseVar.render`
guard may already do that via `is_visible`; confirm before changing.

Then two `render_marker_overlay` calls go through the housing (up to two draws
per cavity per frame). Cavities with no marker skip these. For a housing with
hundreds of cavities, each carrying a marker, that is hundreds of decal draws
per frame. This is the same batching question as `housing.md`.

## Line 163-... (`Cavity.render_selected_overlay`) — gated on `is_selected`, then reads housing internals
Returns immediately unless selected, so no per-frame cost for unselected cavities.
For the selected one it reads `housing_3d._picker` directly (line 191), which
couples the two classes. Not a performance issue, noted for the functional review.
