# harness_designer/ui/dialogs/transition_routing.py

TransitionRoutingDialog -- re-routes wires between a transition's output branches via drag-and-drop (_WireList, _BranchGroup).

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_WireList.dragMoveEvent` (line 123-127): no loops or allocations found.
- `_WireList.dropEvent` (line 130-145): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
