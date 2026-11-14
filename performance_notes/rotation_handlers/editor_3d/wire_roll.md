# harness_designer/rotation_handlers/editor_3d/wire_roll.py

WireRollRings3D(Rings3D) — the single ring that rolls a wire service loop about the wire it sits in (the loop's "Rotate on Wire" context-menu entry; armed through rotation_rings.WireRollRings, not by the right-click that arms the ordinary gizmo).

Cold path (146 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
