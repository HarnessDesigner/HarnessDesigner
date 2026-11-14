# harness_designer/ui/prop_ctrls/events.py

PropertyEvent -- the event object every control's propertyChanged signal carries (name + new value). PropertyValue (TYPE_CHECKING-only) is the union of every value shape a control can emit, including the color control's [name, Color] pair.

Cold path (128 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
