# harness_designer/objects/objects_pegboard/conductor_run.py

The peg-board editor's view of a cable conductor as the schematic draws it: an inert placeholder like circuit.py, so the run can be the selected object (see objects_3d/conductor_run.py). Added 2026-11-13.

Cold path (33 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
