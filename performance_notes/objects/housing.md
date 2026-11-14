# harness_designer/objects/housing.py

The most heavily-loaded wrapper: owns cavities, tpa/cpa locks, seal, cover, and boot, across all three views.

Cold path (173 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
