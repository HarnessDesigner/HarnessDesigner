# performance_notes/ui/log_viewer

Covers `harness_designer/ui/log_viewer/`.

- [viewer.md](viewer.md) - whole-file reads for the date and hour tree, and the copy on every appended batch (the main concerns in this folder)

## Reviewed for performance
`viewer.py` (about 1,160 lines) was read for its model, delegate, append, and tree-loading paths. `logviewer.py` (44 lines) is a thin wrapper and was checked for structure only.

## Functional note (flagged, not fixed)
- `ViewerPanel._populate_hours` has no callers in the package. It is dead code, so its behaviour has not been exercised.
