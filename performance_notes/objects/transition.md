# harness_designer/objects/transition.py

Wrapper for transitions. Model-building/rendering design (OCC boolean pipeline issues, the move to cylinder/sphere primitives, offset/bulb_offset/angle semantics) is in TRANSITION_DESIGN.md; placement/attaching stays in BUNDLE_PLACEMENT.md. Read TRANSITION_DESIGN.md in full before touching transition model-building code.

Cold path (130 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
