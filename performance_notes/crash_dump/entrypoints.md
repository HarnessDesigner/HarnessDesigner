# harness_designer/crash_dump/entrypoints.py

The public, app-facing entry points. run.py's fatal-exception hook and canvas_base.py's per-object render-failure handler call straight into dump_state_on_fatal_exception/dump_render_failure — the same two names the old, single-file crash_dump.py module exposed before this was promoted to a package, so neither call site needed to change. dump_visible_objects is a third, newer entry point: a deliberate, user-triggered (Ctrl+Shift+D) snapshot of whatever a canvas actually drew last frame, rather than something tied to an error at all.

Cold path (210 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
