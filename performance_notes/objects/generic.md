# harness_designer/objects/generic.py

Catch-all one-file-per-part wrapper shape, used for part types without a dedicated file of their own.

Cold path (40 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
