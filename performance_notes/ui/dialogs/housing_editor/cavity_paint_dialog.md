# harness_designer/ui/dialogs/housing_editor/cavity_paint_dialog.py

CavityPaintDialog(QtWidgets.QDialog) + its canvas widget _PaintCanvas -- a standalone 2-D "paint program" style editor for manually laying out circle/rectangle cavities on a flattened (local x/y millimetre) projection of a selected terminal plane, opened from tree_panels.py's "Draw Cavities on Surface..." (toolbar button or right-click menu on a terminal plane_group).

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_PaintCanvas.resizeEvent` (line 271-273): no loops or allocations found.
- `_PaintCanvas.mousePressEvent` (line 276-301): no loops or allocations found.
- `_PaintCanvas.mouseMoveEvent` (line 304-329): no loops or allocations found.
- `_PaintCanvas.mouseReleaseEvent` (line 332-358): no loops or allocations found.
- `_PaintCanvas.keyPressEvent` (line 361-365): no loops or allocations found.
- `_PaintCanvas.paintEvent` (line 368-396): 4 loop(s), QColor x1, QPainter x1.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.
Nested loops (cost grows with the product of the sizes; check the sizes are small): `_merge_clusters` (lines 84-114, depth 2), `_PaintCanvas._rebuild_transform` (lines 168-207, depth 2), `_PaintCanvas.paintEvent` (lines 368-396, depth 2), `CavityPaintDialog._reload_list` (lines 675-694, depth 2).

Status: static read of the code only. Nothing here has been profiled.
