# harness_designer/rotation_handlers/rotation_ring/outer_ring.py

## Line 70-130 (`OuterRing.__init__`) — builds the protractor's outer ring
Creates the outer ring geometry and its tick marks. Runs when the gizmo opens.

## Line 130-135 (`_get_label_color`) — a constant
Returns a fixed grey. Cheap.

## Line 214-240 (`pick_tick`) — tick hit test per mouse move
Tests the tick marks under the cursor against the camera. Runs per mouse move while the protractor is hovered. The tick list is short.

## Line 295-end (`delete`) — teardown
Releases the buffers. Runs once per session.

**Typing (fixed in this pass):** the optional tick result is `_Union["_Tick", None]`.
