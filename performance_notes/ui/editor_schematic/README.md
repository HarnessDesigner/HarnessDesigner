# performance_notes/ui/editor_schematic

Covers `harness_designer/ui/editor_schematic/` (`editor_schematic.py`, plus an empty `__init__.py`).

## Reviewed for performance
Both files were read in full. Nothing in this folder is on a hot path:

- `EditorSchematic` is a thin forwarding wrapper, the same shape as `Editor3D`. Its `set_selected`, `add_object`, `remove_object`, `bind`, `set_clone_obj` and `clear` methods delegate straight to `EditorSchematicPanel`.
- `EditorSchematicPanel.__init__` reads the screen geometry only when the virtual canvas size is unset. That happens once, at first run.
- `EditorSchematicPanel.center_on_object` runs once per selection. It does one centre and at most one zoom, with no loops over objects and no database queries.

## Notes
- `center_on_object` returns early while `is_fit_active` is set, so a selection during the automatic whole-project framing does no camera work.
- The zoom-out delta is negated relative to the 3D panel, because the schematic camera's `Zoom` uses the opposite sign convention. That is correct as written and is not a cost issue.
- Nothing here needs a cache or a worker thread.
