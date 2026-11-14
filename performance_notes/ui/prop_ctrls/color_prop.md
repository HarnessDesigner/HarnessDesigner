# harness_designer/ui/prop_ctrls/color_prop.py

ColorProperty -- wraps ui/widgets/color_ctrl.py's swatch-plus-picker; emits a [name, Color] pair on propertyChanged (see events.PropertyValue). No callers. Known, not fixed: it has the same two faults as BitmapComboBoxProperty (per-keystroke commit, completer never fed).

Cold path (231 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
