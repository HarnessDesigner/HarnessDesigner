# harness_designer/scraping/browser_pick.py

The JS that finds the element under the pointer in the live page and builds a selector, parse_pick() (validates the answer), and pick_snippet().

Cold path (192 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
