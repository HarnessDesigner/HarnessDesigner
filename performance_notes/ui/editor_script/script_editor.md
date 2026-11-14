# harness_designer/ui/editor_script/script_editor.py

The two top-level classes for the scraper tool's Script Editor dock: a code editor for writing/running scraper scripts, with a Claude assistant panel and a run console as tabs underneath.

Cold path (545 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
