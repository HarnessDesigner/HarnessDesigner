# harness_designer/ui/concentric_section/section_model.py

Plain-data description of a bundle cross-section; touches neither the database nor Qt, so layout code can build it headlessly. Millimetres, origin on the bundle axis, +y down.

Cold path (373 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
