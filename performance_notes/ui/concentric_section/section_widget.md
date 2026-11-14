# harness_designer/ui/concentric_section/section_widget.py

ConcentricSectionWidget(QWidget) -- the whole widget: CrossSectionView on the left and WireInfoPanel on the right in a horizontal QSplitter (the same splitter the circuit editor uses; opens 3 : 2). Dragging the sash all the way right closes the information pane and back opens it (set_info_open() / is_info_open() do the same from code).

Calls `processEvents` at line(s) 187: it keeps the UI alive during a long task but lets any other queued event run in the middle of it (re-entrancy risk); a worker thread or chunked work with `CallLater` is the safer shape.

Status: static read of the code only. Nothing here has been profiled.
