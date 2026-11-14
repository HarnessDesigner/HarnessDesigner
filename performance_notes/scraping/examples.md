# harness_designer/scraping/examples.py

EXAMPLES — the script editor's Examples menu, showing how to keep a socket/Event on a thread so a *second* script can end a first script's stuck wait ("Release a stuck script") — the user-facing answer to runner.py's own Stop limitation below.

Cold path (276 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
