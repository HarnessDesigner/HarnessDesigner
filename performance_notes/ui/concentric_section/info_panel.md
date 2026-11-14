# harness_designer/ui/concentric_section/info_panel.py

The right-hand information pane.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `CablePreview.paintEvent` (line 47-57): QPainter x1.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.
`setStyleSheet` inside a loop at line(s) 153: each call re-polishes the widget; set it once on the parent or batch the widgets.

Status: static read of the code only. Nothing here has been profiled.
