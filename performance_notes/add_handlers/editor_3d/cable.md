# harness_designer/add_handlers/editor_3d/cable.py

Subclass of the 3D wire handler (`editor_3d/wire.py`). A cable snaps to nothing, so it overrides the wire session's per-move work with something much smaller.

## `_hover_phase0`, `_hover_phase1` — per move
Each does one `camera.get_position_on_focal_plane(mouse_pos)` and one `_update_preview_stop`, which moves the growing point and calls `editor3d.Refresh(False)` (inherited from [wire.md](wire.md)). There is no `find_object` pick and no compatibility check, so a cable move is one projection plus one repaint. The repaint per move is the only real cost; it is what draws the live preview, so it is needed. It could be skipped only when the projected point did not change.

## `_ensure_snap_probes`
Empty override: the wire handler's per-move probe check is skipped.

## Line 99-128 (`_commit_waypoint`) — once per click
Builds a list of the cable's waypoints (`row.point.as_numpy` for each) and one distance to the previous point, then calls the base commit. One click, a handful of points. Not a concern.
