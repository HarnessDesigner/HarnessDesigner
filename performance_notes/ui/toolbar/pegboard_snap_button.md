# harness_designer/ui/toolbar/pegboard_snap_button.py

PegboardSnapButton(QtWidgets.QToolButton) -- Peg Board grid-snap toggle, same left/right-click shape as snap_angle_button.py's SnapAngleButton: left click enables/disables with a checkbox icon overlay (icon icons.mip_mapping, the only checkerboard/grid-like icon asset available -- no dedicated grid icon exists), right click opens a popup with an "Auto" QCheckBox + QDoubleSpinBox (no enumerable fixed-value set like snap angle has, so no AutoCompleteComboBox here).

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `PegboardSnapButton.mousePressEvent` (line 150-156): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
