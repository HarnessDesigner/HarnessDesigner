# harness_designer/objects/seal.py

One-file-per-part wrapper, same shape as cover.py/boot.py. Seal rendering for freshly-placed terminals participates in the Terminal delete/wire-detach/reconnect work described under terminal.py below.

Cold path (80 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
