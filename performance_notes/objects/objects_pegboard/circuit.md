# harness_designer/objects/objects_pegboard/circuit.py

The peg-board editor's view of a circuit: an inert placeholder (BasePegboard built with no vbo/angle/position/scale/material, never visible, obb None), built like a Note that was never placed in this editor. A circuit has nothing to draw; the view exists so the canvas can hold the circuit as its one selected object (see objects/circuit.py).

Cold path (49 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
