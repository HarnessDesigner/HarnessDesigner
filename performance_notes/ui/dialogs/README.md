# performance_notes/ui/dialogs

Covers `harness_designer/ui/dialogs/`.

- [housing_editor/housing_editor.md](housing_editor/housing_editor.md) - surface overlay repaint cost, draw-mode mouse moves, wire-surface containment loop (the main concern in this folder)
- [bom_dialog.md](bom_dialog.md) - four synchronous report builds on open, and two rebuilds per excess-percentage step
- [export_dialog.md](export_dialog.md) - synchronous mesh gathering on the UI thread
- [part_orientation.md](part_orientation.md) - per-rotation recentre and forward/up recompute (small)

## Reviewed for performance
The four files above were read for their hot paths. These were checked for structure, typing and event handling only, and have no notes yet:

- `part_search.py` (about 2,430 lines). Only the `GetValue` path changed in this pass. Its results view is an `EditorList` page, so the paging and load behaviour belong to the `ui/editor_db` notes, not to this file.
- `transition_editor/dialog.py` and `transition_editor/preview.py`
- `render_setings.py` (read in full; nothing on a hot path beyond widget construction)
- `transition_routing.py`, `dimensions_dialog.py`, `cavity_panel.py`, `tree_panels.py`, `connector_analysis.py`, `analysis_panel.py`, `housing_obj.py`, `cavity_obj.py`, `accessory_panel.py`, `housing_panel.py`, `debug_settings.py`, `project_dialog.py`, `add_project.py`, `add_note.py`, `bundle_wires_dialog.py`, `header.py`, `dialog_base.py`, `error.py`, `properties_dialog.py`

`connector_analysis.py` is the one of those most likely to matter for speed: it runs pure-Python BFS and per-candidate containment loops over the mesh surfaces. It needs its own pass before any claim about its cost.

## Functional issues seen while typing (flagged, not fixed)
- `bundle_wires_dialog.py` `_wire_label` and `_effective_diameter` read `.wire` from each item, but the items come from `PJTBundle.wires`, which returns `PJTWire` rows directly. Any bundle that has wires raises `AttributeError` when the dialog opens.
- `render_setings.py`: `RenderSettingsDialog` is opened with the ray-tracing dialog as its parent, but `BaseDialog` is annotated for `MainFrame`. `self.mainframe` then holds the wrong object. Nothing in the render-settings code reads `.mainframe` today.
- `header.py` assigns `self.setFrameShape = lambda *a: None` on the instance, which silently disables `setFrameShape` for that header.
- `bom_dialog.py` `_reload_all`, `_on_wire_excess_changed` and `_on_bundle_excess_changed` check `project is None`, but `MainFrame.project` loops until a project is open and never returns `None`. Those branches cannot run.
