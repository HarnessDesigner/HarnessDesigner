# harness_designer/ui/pegboard_table/mdi_host.py

PegboardTableHost(QtWidgets.QMdiArea) and _CursorAndCloseFilter(QtCore.QObject) -- hosts a wire_table.WireTable inside an off-screen QMdiSubWindow purely so its rendered appearance can be grabbed as a texture (the same WA_DontShowOnScreen + .grab()-to-GL-texture technique explored for the Peg Board Editor's floating spreadsheet-style overlay tables; see harness_designer/ui/editor_pegboard/MAP.md DESIGN NOTES's Peg Board Editor entries for the fuller story of why a real Qt widget grabbed to a texture was chosen over a from-scratch GL-drawn table). _CursorAndCloseFilter.eventFilter intercepts cursor/close-button events on the hosted sub-window so they still behave sensibly despite the host never actually being shown on a real screen.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_CursorAndCloseFilter.eventFilter` (line 171-181): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.
Calls `processEvents` at line(s) 349: it keeps the UI alive during a long task but lets any other queued event run in the middle of it (re-entrancy risk); a worker thread or chunked work with `CallLater` is the safer shape.

Status: static read of the code only. Nothing here has been profiled.
