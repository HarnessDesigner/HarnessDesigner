# performance_notes/add_handlers

Covers `harness_designer/add_handlers/` (`base.py`, `editor_3d/`, `editor_pegboard/`, `editor_schematic/`). The `__init__.py` files hold only the copyright line and have no notes.

## Hot path
An add session is driven by `AddHandlerBase.__call__`, which the canvas calls for every mouse event. `MOVE` events run the handler's `hover` (or `_follow` / `_hover_*`), so per-move work is what matters. `LEFT_UP`, `RIGHT_UP` and `CANCEL` run once per click and are not a concern.

## Common per-move costs
- `gl.object_picker.find_object` ray-casts the bounds pools (`ArrayPool.hit_test`, vectorised) and then runs the per-triangle test on the surviving candidates. Every editor's `hover` that snaps to an object calls it.
- `utils.snap_pool.SnapPool.query` and `query_ray` are vectorised, but the `snap_pool` property on several handlers rebuilds the Python lists and the `np.array` on every access. Each `hover` reads it once.
- `self.mainframe.editorX.Refresh(False)` and `editor.update()` repaint the view on every move. These are the most expensive calls on the move path after the picker.
- Several handlers wrap the move in `with self.mainframe.editor3d.context:`, which makes the GL context current on every move.

## Module notes
The per-module files in this tree have the details. The notes for `cpa_lock`, `cover`, `tpa_lock`, `housing` and `note` are short because they repeat the same pattern, and they say where they differ.

## Status
Nothing here has been profiled. Each point is a candidate taken from reading the code, and each needs a measurement before anyone changes it. Several of these handlers run once per placement, so most of their cost is not on any hot path.
