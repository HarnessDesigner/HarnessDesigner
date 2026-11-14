# harness_designer/ui/concentric_section/section_host.py

ConcentricSectionHost(QMdiArea) -- hosts a ConcentricSectionWidget in a hidden QMdiSubWindow exactly as ui/pegboard_table/mdi_host.py's PegboardTableHost hosts a wire table (never shown on a real screen; real Qt title bar, close button, drag-to-move and drag-to-resize), and imports that module's coordinate constants rather than copying them (SUB_WINDOW_ANCHOR, PIXELS_PER_MM, the rest point, the oversized area, _CursorAndCloseFilter), so a section and a table share one coordinate frame.

Calls `processEvents` at line(s) 152: it keeps the UI alive during a long task but lets any other queued event run in the middle of it (re-entrancy risk); a worker thread or chunked work with `CallLater` is the safer shape.

Status: static read of the code only. Nothing here has been profiled.
