# harness_designer/add_handlers/editor_3d/wire.py

This is the most expensive handler on the move path. Per move:
- `_ensure_snap_probes`: a cheap check, but it rebuilds the `SnapProbeSet` when the part changes.
- `find_object` in `_hover_extension`, `_hover_phase0`, `_hover_phase1`, and `_handle_second_click`.
- `check_terminal_compat` / `check_splice_compat` whenever a target is under the cursor.
- `_update_preview_stop`, which calls `self.mainframe.editor3d.Refresh(False)`. That repaints the 3D view on every move. It is the candidate to measure first. The repaint may be needed to show the live preview, but it may be redundant when the position did not change.
- `_overlay.show_message` / `hide_message` on every move.

Candidates to measure before any change: skip the `Refresh` when the snapped position is unchanged, and skip the compat check when the target did not change since the last move.

Not on a hot path: `_handle_first_click`, `_handle_second_click` (once per click), `_commit_growing_point_as_waypoint`, `finalize_at_last_point`, and `cancel`.
