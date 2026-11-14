# harness_designer/objects/bundle_layout.py

Companion to bundle.py — same 3D + peg-board-only scope and same BUNDLE_DESIGN.md/BUNDLE_PLACEMENT.md design docs.

Cold path (62 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
