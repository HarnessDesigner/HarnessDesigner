# harness_designer/handlers/bundle_layout_handler.py

## Line 25-40 (`_bundle_segments`) — builds a list of segments on each call
Same pattern as `wire_layout_handler._wire_segments`. Called once per bundle inside `_find_bundle`'s loop.

## Line 43-82 (`_find_bundle`) — scans every bundle on each miss
Same problem as `wire_layout_handler._find_wire`: when the picker misses, every bundle in the project is tested segment by segment in Python on every mouse move. The number of bundles is usually smaller than the number of wires, so the cost is lower, but the pattern is the same. The same fix applies (limit candidates by bounding box, or cache the segment list per camera change).

## Line 85-111 (`_find_insertion_index`) — one pass over one bundle's segments
Runs when a waypoint is inserted. Fine.

## Line 114-174 (`_create_bundle_layout_at_endpoint`, `_create_bundle_layout_on_bundle`) — database writes on click
One point insert, one path row, one layout row and one view refresh per click. Fine.
