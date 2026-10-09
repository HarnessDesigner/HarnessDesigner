# performance_notes/ui/editor_3d

Covers `harness_designer/ui/editor_3d/` (`editor_3d.py`, plus an empty `__init__.py`).

## Reviewed for performance
Both files were read in full. Nothing in this folder is on a hot path:

- `Editor3D` and `Editor3DPanel` are thin forwarding wrappers. Every method (`set_selected`, `add_object`, `remove_object`, `bind`, `set_clone_obj`, `clear`) delegates straight to the canvas.
- `Editor3DPanel.__init__` reads the screen geometry only when the virtual canvas size is unset. That happens once, at first run, and the result is saved to config.
- `Editor3DPanel.center_on_object` runs once per selection. It does one centre and at most one zoom, with no loops over objects or DB queries.

## Notes
- `center_on_object` returns early while `is_fit_active` is set, so a selection during the automatic whole-project framing does no camera work. This is the intended cheap path.
- Nothing here needs a cache or a worker thread.
