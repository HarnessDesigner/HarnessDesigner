# harness_designer/ui/widgets/text_ctrl.py

TextCtrl -- a thin QWidget wrapper pairing a native Qt line edit with this app's signal/validation conventions; backs ui/prop_ctrls/string_prop.py.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `TextCtrl._on_text_changed` (line 125-134): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.
Timers / deferred calls: line 133 (singleShot), line 145 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.

Status: static read of the code only. Nothing here has been profiled.
