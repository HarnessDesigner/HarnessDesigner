# harness_designer/ui/dialogs/housing_editor/housing_editor.py

## `SurfaceOverlay.paintEvent` - projects every triangle in Python on every paint
Each paint walks every selected surface (wire plane groups, terminal surfaces, cavity surfaces) and, for each triangle, calls the nested `project()` three times. `project()` builds a fresh 4-element `np.array`, does a 4x4 matrix-vector product, and returns a `QPointF`. It is called once per vertex per triangle, so a paint over a large housing mesh is tens of thousands of small numpy calls, and each `draw_surf` also builds a `QPolygonF` and draws it one triangle at a time.

Candidate fixes, to be measured before adopting:
- Project all vertices once per paint in a single matmul (`verts_h @ clip_mat.T`, one call), then index the result per triangle. This is one large vector operation rather than many small ones, so it is not the same case as the small-call scalar scatter the codebase's hot-path notes warn about.
- Cache the projected vertex array keyed by the camera's clip matrix and viewport. Overlay repaints during mouse moves would then skip the projection entirely.
- Batch each group's triangles into one `QPainterPath` and fill it once, instead of `drawPolygon` per triangle.

## `_SurfaceSelectFilter.eventFilter` - draw mode calls `update()` on every mouse move
While `dlg.draw_mode` is set, every `MouseMove` with a draw in progress calls `_update_draw`. If that path calls `surface_overlay.update()`, each move schedules a full `SurfaceOverlay.paintEvent` above, so the cost in the previous section is paid once per mouse event rather than once per visible change. This needs a check of what `_update_draw` calls.

## `_match_wire_surface` - containment and area recomputed per candidate
For each terminal, the method loops over every wire surface candidate. For each candidate it:
- normalises the surface normal (a fresh `astype` copy each time),
- projects the boundary points onto the candidate's plane (vectorised over the boundary, which is fine),
- calls `_analysis.surface_contains_points` and `_analysis.surface_area` for the candidate.

`surface_area` depends only on the candidate surface and `self.vertices`, so its value could be computed once per surface and cached on the dialog for the duration of a load. The fallback branch then calls `surface_centroid` again for every candidate. The centroid is also a per-surface value, so the same cache would cover it. The cost is O(terminals x candidates), so it grows with both.

## `SetValue` - rebuilds the whole analysis on open
`SetValue` constructs the `Housing` facade (which builds cavities and 3D/schematic/pegboard views) and then runs the surface analysis. This happens once per dialog open, which is acceptable. The per-cavity and per-terminal analysis inside it should be checked the same way as the containment loop above.
