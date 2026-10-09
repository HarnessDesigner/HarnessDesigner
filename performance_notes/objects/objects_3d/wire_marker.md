# harness_designer/objects/objects_3d/wire_marker.py

## Line 235-262 (`WireMarker._update_position`) — builds a `Line` on every endpoint move
Each call constructs `_line.Line(self._p2, self._p1)` (line 247) and computes
its length, even when the event came from the marker's own position. The line
is needed for both branches, so the cost is one small allocation per event.
Fine for a marker that moves at mouse-drag rate.

Does not call `super()`, so the base `BaseVar` update path (context acquire,
`_o_position` copy, `Refresh`) is skipped. That is a functional question for the
review; noted here because it also avoids the per-event GL-context cost.

## Line 252-262 — `_percent_for_point` and `_point_for_percent` on every move
Two small geometry helpers per event. Cheap; no change recommended.
