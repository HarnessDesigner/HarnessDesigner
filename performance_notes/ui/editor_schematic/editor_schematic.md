# harness_designer/ui/editor_schematic/editor_schematic.py

Defines EditorSchematic(DockBase) — the dock wrapper, and EditorSchematicPanel(gl.canvas2d.CanvasSchematic) — the GL canvas (actual import alias is _canvas_schematic), for the flat/simplified top-down "schematic" view of the harness (distinct from the Peg Board Editor's manufacturing-formboard view — see harness_designer/ui/editor_pegboard/MAP.md DESIGN NOTES's Peg Board Editor entry for why the two are kept separate).

Cold path (204 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
