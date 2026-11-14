# harness_designer/ui/dialogs/header.py

Header(QtWidgets.QWidget) -- the custom draggable title-bar replacement every BaseDialog uses in place of the native OS title bar.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `Header.resizeEvent` (line 76-94): QPixmap x1.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.
Qt objects created inside a loop: `QFontMetrics` (line 113).

Status: static read of the code only. Nothing here has been profiled.
