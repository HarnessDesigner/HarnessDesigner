# harness_designer/scraping/script_files.py

read_script(), write_script() (atomic write), scratch_path() (the autosaved working copy path).

Cold path (57 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
