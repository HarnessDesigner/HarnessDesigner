# harness_designer/ui/widgets/tri_state_checkbox_ctrl.py

_TriStateCheckBox/TriStateCheckboxCtrl -- a checkbox supporting an indeterminate third state, backing ui/prop_ctrls/tri_state_checkbox_prop.py.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_TriStateCheckBox.sizeHint` (line 161-163): no loops or allocations found.
- `_TriStateCheckBox.mousePressEvent` (line 169-172): no loops or allocations found.
- `_TriStateCheckBox.keyPressEvent` (line 175-184): no loops or allocations found.
- `_TriStateCheckBox.focusInEvent` (line 187-195): no loops or allocations found.
- `_TriStateCheckBox.enterEvent` (line 198-200): no loops or allocations found.
- `_TriStateCheckBox.leaveEvent` (line 203-205): no loops or allocations found.
- `_TriStateCheckBox.paintEvent` (line 226-269): QBrush x1, QPainter x1, QPen x2.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.

Status: static read of the code only. Nothing here has been profiled.
