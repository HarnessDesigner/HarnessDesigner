# performance_notes/ui/editor_pegboard

Covers `harness_designer/ui/editor_pegboard/` (`editor_pegboard.py`, plus a small `__init__.py`).

## Reviewed for performance
Both files were read in full. Nothing in this folder is on a hot path:

- `EditorPegboard` is a thin forwarding wrapper, the same shape as `Editor3D` and `EditorSchematic`.
- `EditorPegboardPanel.__init__` reads the screen geometry only when the virtual canvas size is unset. That happens once, at first run.
- `EditorPegboardPanel.center_on_object` runs once per selection. It does one centre and at most one zoom, with no loops over objects and no database queries.
- `EditorPegboardPanel.set_clone_obj` is a documented no-op, since the peg board has no clone model yet. It costs nothing.

## Notes
- `center_on_object` reads the peg board position from `obj.objpegboard`, not from `obj`. That is the intended anchor, not a cost issue.
- Nothing here needs a cache or a worker thread.
