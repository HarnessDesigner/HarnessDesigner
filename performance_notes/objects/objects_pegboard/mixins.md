# harness_designer/objects/objects_pegboard/mixins.py

## Line 76-... (_point_on_wire via the shared WireTypeMixin) - walks every segment per mouse event
The peg-board wire-layout click path projects the mouse position onto the closest point of each wire segment. That is one pass over the segments per mouse event over a wire, which is linear in the segment count. Wires have few segments, so the cost is small. The segment list comes from the shared _segments() walk, so any caching of segment transforms in wire.md would also cover this path.

## Line 49-56 (_waypoints, _closest_point_on_segment_xz) - small per-call work
_waypoints is now a direct attribute read. _closest_point_on_segment_xz does a few float operations per segment. No change needed.
