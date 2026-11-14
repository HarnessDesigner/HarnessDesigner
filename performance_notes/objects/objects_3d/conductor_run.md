# harness_designer/objects/objects_3d/conductor_run.py

The 3D editor's view of a cable conductor as the schematic draws it (objects/cable_conductor.py ConductorRun): an inert placeholder built like circuit.py (no vbo/angle/position/scale/material, never visible, not pickable), so the run can be the selected object without the canvas logging the selected ConductorRun has no view in the editor3d canvas (user's log, 2026-11-12).

Cold path (41 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
