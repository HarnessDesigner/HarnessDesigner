# performance_notes/add_handlers

Covers `harness_designer/add_handlers/` (`base.py`, `editor_3d/`, `editor_pegboard/`, `editor_schematic/`). The `__init__.py` files have short notes of their own (they hold docstrings only).

## Hot path
An add session is driven by `AddHandlerBase.__call__`, which the canvas calls for every mouse event. `MOVE` events run the handler's `hover` (or `_follow` / `_hover_*`), so per-move work is what matters. `LEFT_UP`, `RIGHT_UP` and `CANCEL` run once per click and are not a concern.

## Common per-move costs
- `gl.object_picker.find_object` ray-casts the bounds pools and then runs the per-triangle test on the surviving candidates. Every editor's `hover` that snaps to an object calls it.
- `snap_pool` on the `cover`, `cpa_lock`, `tpa_lock`, `seal` and `terminal` handlers (`editor_3d/*.py`, a `@property`) rebuilds its Python lists and the `SnapPool` arrays on every access, and `hover` reads it once per move. These are the clearest fixes in this folder: build the pool once per session. Memory price: one pool of `N x 3` floats (a few KB for hundreds of housings, `terminal.py` a few tens of KB for thousands of cavities). Speed gain: removes an O(N) Python loop per move. Worth doing; the memory is negligible and the pool lives only as long as the session. Invalidate it only if the housing or cavity set can change while a session is open (it cannot today).
- `self.mainframe.editorX.Refresh(False)` / `editor.update()` repaint the view on every move (`editor_3d/wire.py` `_update_preview_stop`, `_update_source_endpoint`; `editor_pegboard/wire.py` hover; `editor_schematic/wire.py` `_ghost_to`). After the picker these are the most expensive calls on the move path.
- Several handlers wrap the move in `with self.mainframe.editor3d.context:` (`editor_3d/wire.py` hover, `bundle.py`, `wire_service_loop.py`), which makes the GL context current on every move.

## Module notes
The per-module files in this tree have the details. The notes for `cpa_lock`, `cover`, `tpa_lock`, `housing` and `note` are short because they repeat the same pattern and say where they differ. `editor_3d/cable.py` (new) is a thin subclass of the wire handler and adds nothing per move.

## Status
Nothing here has been profiled; each point comes from reading the code and needs a measurement first. Most of these handlers do their expensive work once per placement, not per move.
