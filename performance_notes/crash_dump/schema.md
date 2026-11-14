# harness_designer/crash_dump/schema.py

The per-class capture-list vocabulary: Attr(name, severity) — one capturable attribute/property name and the dump severity it requires. dump_property(severity) — a decorator for a @property's plain getter function (must be stacked *below* @property, closer to def, since a property object itself has no __dict__ to stash the tag on); marks it capturable at the given severity for registry.py's @capturable to pick up.

Cold path (45 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
