# harness_designer/ui/widgets/editable_tab_ctrl.py

EditableTabBar/EditableTabCtrl -- a QTabWidget whose tab labels can be renamed in place.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `EditableTabBar.mouseDoubleClickEvent` (line 98-108): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
