# harness_designer/plugins/plugins/claude_ai/qt/gui_call.py

call_in_gui() — lets a tool running on the worker thread ask the user something and block until the GUI answers, without the caller needing to manage threading itself.

Cold path (114 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
