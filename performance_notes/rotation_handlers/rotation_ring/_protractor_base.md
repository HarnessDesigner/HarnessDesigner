# harness_designer/rotation_handlers/rotation_ring/_protractor_base.py

## Line 106-200 (`__init__`, `set_radii`, `delete`) — protractor set-up and teardown
Creates the protractor's geometry and GPU buffers, and releases them on delete. Runs when the rings open and close.

## Line 310-369 (`set_radii`, `delete`) — rebuild on radius change
A radius change rebuilds the geometry. Runs when the view size changes the ring size, not per frame.

## Line 750-759 (`_get_label_color`, `_set_solid_color`) — colour set-up
Chooses the label and solid colours. Cheap; called when the ring is built or highlighted.
