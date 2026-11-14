# harness_designer/ui/widgets/stipple_ctrl.py

StippleEditor/StippleCtrl -- edits a bit-pattern line-stipple value, used for dashed/dotted line rendering styles.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `StippleEditor.mousePressEvent` (line 114-120): no loops or allocations found.
- `StippleEditor.mouseMoveEvent` (line 123-127): no loops or allocations found.
- `StippleEditor.mouseReleaseEvent` (line 130-132): no loops or allocations found.
- `StippleEditor.paintEvent` (line 136-148): 1 loop(s), QPainter x1, QPen x1.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.

Status: static read of the code only. Nothing here has been profiled.
