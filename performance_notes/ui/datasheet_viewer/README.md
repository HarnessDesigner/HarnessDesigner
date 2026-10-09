# performance_notes/ui/datasheet_viewer

Covers `harness_designer/ui/datasheet_viewer/viewer.py` (288 lines) and an empty `__init__.py`.

## Reviewed for performance
The whole module was read. Nothing here is expensive:

- `ImageViewer.paintEvent` builds one `QTransform` and draws the pixmap once per paint. Scaling happens inside the painter, so there is no per-paint image resampling.
- `ImageViewer.mouseMoveEvent` schedules `update` with `QTimer.singleShot(0, ...)`. That coalesces repaints during a drag.
- `PDFViewer` renders through `QtPdfWidgets.QPdfView`, which does its own page caching. Nothing in this module re-renders pages.
- The image is loaded once, in the constructor, from the path it is given.

## Functional issues (flagged, not fixed)
- `ImageViewer.wheelEvent` changes `self.scale` by `angleDelta / 8000` with no lower bound. Enough wheel steps take the scale to zero or below. At zero nothing draws, and below zero the image is flipped.
- `ImageViewer.mouseMoveEvent` clamps the pan offsets using the unscaled `pixmap.width()` and `height()`, but `paintEvent` draws the pixmap at `scale`. When the image is zoomed, the clamp limits are wrong, so the pan can stop early or let the image leave the window.
