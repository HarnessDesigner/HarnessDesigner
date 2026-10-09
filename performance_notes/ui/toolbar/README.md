# performance_notes/ui/toolbar

Covers `harness_designer/ui/toolbar/`.

- [toolbar.md](toolbar.md) - icon compositing on every selection change (the main concern in this folder)

## Reviewed for performance
`toolbar.py` (about 1,600 lines) was read for its selection and icon paths. `float_spin_button.py`, `pegboard_snap_button.py`, `pegboard_drag_mode_button.py`, and `snap_angle_button.py` were checked for structure and event handling only. None of them is on a per-frame path.
