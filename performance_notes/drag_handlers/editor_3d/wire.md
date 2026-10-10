# harness_designer/drag_handlers/editor_3d/wire.py

Per move: `_move_delta` (projections, cheap) and the snap checks against the wire's ends. The snap probe set is queried on each move; the cost depends on how many probes exist. Not profiled. This is the drag handler to measure first among the 3D ones.
