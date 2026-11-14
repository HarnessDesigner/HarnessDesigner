# harness_designer/ui/toolbar/snap_angle_button.py

SnapAngleButton(QtWidgets.QToolButton) -- rotation-snap toggle: left click enables/disables with a checkbox icon overlay, right click opens an AutoCompleteComboBox (from ui/widgets/autocomplete_combobox.py) popup of the 71 valid snap angles. Writes Config.editor3d.rotation_rings.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `SnapAngleButton.mousePressEvent` (line 146-152): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
