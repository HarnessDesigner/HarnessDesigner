# harness_designer/objects/cable_conductor.py

CableConductor(ObjectBase) (, 5b stage 3): the JUNCTION of one cable conductor's two leads, modelled on wire_service_loop.py (two ends, a wire on each). It is what Wire.start_sibling / stop_sibling return for the split end of a lead (the lead's stop point is the conductor's split point).

Timers / deferred calls: line 428 (singleShot), line 434 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.
Nested loops (cost grows with the product of the sizes; check the sizes are small): `lead_node` (lines 74-97, depth 2).

Status: static read of the code only. Nothing here has been profiled.
