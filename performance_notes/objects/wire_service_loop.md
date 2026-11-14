# harness_designer/objects/wire_service_loop.py

Part of the wire family, all three views. delete() (2026-10-26) takes the loop out of its wire: it merges the two wires either side of it with handlers.wire_topology.merge_wires_in_place (ordered by which one ENDS at one of the loop's points, not by start_sibling/stop_sibling: start_sibling is the wire AFTER the loop, the one that starts at its START point, and stop_sibling the wire BEFORE it -- Project._reconcile_wire_sibling_graph sets them from the saved ids), deletes the two WireLayouts split_wire_for_loop put at the loop's points, then the loop.

Cold path (223 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
