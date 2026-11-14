# harness_designer/ui/editor_pegboard/editor_pegboard.py

Defines EditorPegboard(DockBase) — the dock wrapper, and EditorPegboardPanel(gl.canvas_pegboard.CanvasPegboard) — the GL canvas, for the Peg Board Editor: a top-down "manufacturing formboard" view of the harness (real 3D part meshes reused flat, bundle strands instead of individual wires except bare-terminated ones; see this file's DESIGN NOTES's "Peg Board Editor" entries for the full multi-phase architecture history).

Cold path (322 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
