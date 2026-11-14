# harness_designer/ui/dialogs/pegboard_print_dialog.py

PegboardPrintDialog(BaseDialog) -- File > "Print Peg Board...". Modal; the main window keeps one instance (MainFrame.show_pegboard_print, which calls refresh() to re-read the peg board's content bounds, then exec()).

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_LayoutPreview.paintEvent` (line 71-122): 2 loop(s), QColor x5, QPainter x1, QPen x2.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.
Calls `processEvents` at line(s) 495: it keeps the UI alive during a long task but lets any other queued event run in the middle of it (re-entrancy risk); a worker thread or chunked work with `CallLater` is the safer shape.
Qt objects created inside a loop: `QPen` (line 108), `QColor` (line 108).

Status: static read of the code only. Nothing here has been profiled.
