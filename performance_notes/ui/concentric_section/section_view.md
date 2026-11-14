# harness_designer/ui/concentric_section/section_view.py

CrossSectionView(QWidget) -- the custom-drawn left pane. Draws the bundle outline, the layer guide rings and every placed cable (wire_painter); click selects a cable (cable_selected), dragging moves the WHOLE cable and all its conductors together (cable_moved, then cable_move_finished -- the place to save).

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `CrossSectionView.paintEvent` (line 147-150): QPainter x1.
- `CrossSectionView.mousePressEvent` (line 173-188): no loops or allocations found.
- `CrossSectionView.mouseMoveEvent` (line 191-204): no loops or allocations found.
- `CrossSectionView.mouseReleaseEvent` (line 207-215): no loops or allocations found.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.

Status: static read of the code only. Nothing here has been profiled.
