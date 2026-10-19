## FILES

#### __init__.py

Package init for the schematic editor dock; no content beyond the standard package marker.

#### editor_schematic.py

Defines `EditorSchematic(DockBase)` — the dock wrapper, and `EditorSchematicPanel(gl.canvas2d.CanvasSchematic)` — the GL canvas (actual import alias is `_canvas_schematic`), for the flat/simplified top-down "schematic" view of the harness (distinct from the Peg Board Editor's manufacturing-formboard view — see MEMORY.md's Peg Board Editor entry for why the two are kept separate). **Naming note**: CODEBASE_MAP.md's `ui/` section refers to this editor as `editor_2d/editor2d.py` (`Editor2D`/`Editor2DPanel`); the real directory and file on disk are `editor_schematic/editor_schematic.py` (`EditorSchematic`/`EditorSchematicPanel`) — same content, renamed. Treat any CODEBASE_MAP.md or MEMORY.md reference to `editor_2d`/`editor2d.py`/`Editor2D` as describing this file. `EditorSchematic` exposes `context`, `set_selected`/`add_object`/`remove_object`/`set_clone_obj`/`clear`/`bind` — thin forwards to `EditorSchematicPanel`, the same shape as `editor_3d.Editor3D`. `EditorSchematicPanel.center_on_object(obj)` pans/zooms the camera to frame a given object — the pattern `editor_pegboard.EditorPegboardPanel.center_on_object` explicitly mirrors. MEMORY.md documents an in-progress unification (`gl/new_canvas2d/`) of this editor's canvas with the Peg Board Editor's canvas, plus a bigger shift away from the dedicated 2D shader toward rendering the schematic view via the real 3D pipeline under an orthographic top-down camera — that work lives under `gl/`, not in this directory, but it may eventually change what `EditorSchematicPanel` renders through.
