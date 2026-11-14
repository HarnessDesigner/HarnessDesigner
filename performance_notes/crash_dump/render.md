# harness_designer/crash_dump/render.py

Per-type rendering: how to label/format a captured value and what counts as its children, consulted only *after* the capture-schema registry has already decided a value is NOT itself a walkable, schema'd app object (those stay $refs, handled entirely by walker.py).

Cold path (101 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
