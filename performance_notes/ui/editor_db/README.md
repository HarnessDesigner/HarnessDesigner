# performance_notes/ui/editor_db

Covers `harness_designer/ui/editor_db/`.

- [base.md](base.md) - `EditorList` (paged SQL, icon cache, COUNT on filter change). The main hot path.
- [wire.md](wire.md) - `WiresPage` swatch icons.
- [edit_dialog.md](edit_dialog.md) - edit dialog open/close.

The table-definition modules (`accessory.py`, `boot.py`, `bundle_cover.py`, `cover.py`, `cpa_lock.py`, `housing.py`, `seal.py`, `splice.py`, `terminal.py`, `tpa_lock.py`, `transition.py`, `wire_marker.py`) contain only class attributes and no functions, so they have no per-row or per-frame code and no notes.

`editordb.py` (19 functions, no loops) was checked structurally only. Its accessor methods are not on the row-level path, but its body was not read line by line in this pass.
