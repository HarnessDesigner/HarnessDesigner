# harness_designer/plugins/ai/job.py

Job — one instruction a call site hands to an AI Session; subclassed by the call site itself, never by a plugin. on_progress/on_usage may fire any number of times; exactly one of on_complete/on_error fires once, terminal. None of these run on the GUI thread — call_after(fn, *args) (forwards to app.CallAfter) is the only sanctioned way a subclass touches a widget.

Cold path (54 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
