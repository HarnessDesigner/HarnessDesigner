# harness_designer/ui/datasheet_viewer/viewer.py

ImageViewer(QtWidgets.QWidget) -- __init__(self, parent, img: str); a pan/zoom viewer for a part's datasheet/CAD preview image, built on QtPdf/QtPdfWidgets so it can show either a plain raster image or a PDF page through the same widget. Handles its own mousePressEvent for drag-panning.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `ImageViewer.mousePressEvent` (line 49-61): no loops or allocations found.
- `ImageViewer.mouseReleaseEvent` (line 64-76): no loops or allocations found.
- `ImageViewer.mouseMoveEvent` (line 79-114): no loops or allocations found.
- `ImageViewer.wheelEvent` (line 117-126): no loops or allocations found.
- `ImageViewer.paintEvent` (line 129-150): QPainter x1, QTransform x1.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.
Timers / deferred calls: line 114 (singleShot), line 126 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.

Status: static read of the code only. Nothing here has been profiled.
