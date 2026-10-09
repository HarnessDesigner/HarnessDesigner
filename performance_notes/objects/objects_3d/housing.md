# harness_designer/objects/objects_3d/housing.py

## Line 876-896 (`Housing.render`) — GL state readback on every frame, for every housing
`if not any(GL.glGetBooleanv(GL.GL_COLOR_WRITEMASK)):` runs on every render
call, for every housing in the scene, every frame. `glGetBooleanv` is a
synchronous query: the CPU waits for the driver to return the current
state, which can stall the pipeline. The comment describes this check as
meant for the selected translucent object's depth-only pass, but the code
does not check selection first, so it runs for all housings. With 200
housings, that is 200 synchronous readbacks per frame.

Fix options:
- Track the color-mask state on the canvas (it already owns the render-pass
  sequencing in `canvas_base._draw_scene`) and read a Python flag instead of
  querying GL.
- Or move the check to the selected-object path so it only runs when
  `is_selected` is true (the only case the comment is about).

This is the highest-impact item in this file. The comment at lines 879-894
says the stutter was caused by the overlay decals on the selected housing.
This query runs even when nothing is selected, so it is a separate cost that
should be fixed independently.

## Line 901-917 (`_render_terminal_overlays`) — walks every cavity and resolves every terminal, each frame
For every housing in the color pass, this iterates `self.db_obj.cavities`,
looks up `cavity.terminal`, calls `terminal_db.get_object()`, and calls
`render_cavity_overlay` (which in turn calls `_refresh_overlay_state`). That is
O(cavities) per housing per frame, plus the lookups. The results change only
when a cavity's terminal changes, so the list of terminal objects per housing
could be cached and invalidated on terminal add/remove.

## Line 217-219 (`Housing.cavities`) — builds a new list on every access
The property comprehension runs on every read. It is called from
`_pick_marker` (line 645, per click), `match_cavity_surfaces` (line 421, once
per model load), and anywhere else that reads it. For a few hundred cavities
this is fine per access, but it is an allocation on every read in the picking
path. Caching the list and invalidating it on cavity add/remove would avoid
the allocation.

## Line 619-673 (`_pick_marker`) — per-click loop over all markers, which is fine
One pass over every cavity's two markers, with a cheap ray-plane test per
marker. O(cavities) per click, no allocations beyond the loop variables. The
only cost worth noting is the `self.cavities` allocation covered above.

## Line 404-466 (`match_cavity_surfaces`) — expensive, but cached on the part singleton
Surface computation is cached on `self._part.mesh_surfaces` (line 413), so
only the first placement of a catalog part pays the full cost. The per-cavity
loops (lines 428-469) run once per match, which is a model load. Not a
per-frame cost.

## Line 716-810 (`_draw_overlay_faces`, `render_surface_overlay`) — decal draw per call
Each overlay face is drawn with its own state toggles (depth offset, depth
mask, and program binds). Called once per overlaid surface per frame. The
overlay caches (`_overlay_vbos`, `_overlay_positions`, `_overlay_geom_cache`)
already avoid rebuilding geometry. Batching overlays that share a program
would reduce the state churn.
