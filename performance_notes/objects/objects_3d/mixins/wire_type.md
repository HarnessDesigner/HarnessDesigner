# harness_designer/objects/objects_3d/mixins/wire_type.py

## `_point_on_wire` and `_closest_point_on_segment_to_ray` — per mouse event, walks every segment
`_point_on_wire` tries every sub-segment of the wire and keeps the closest hit,
calling `unproject_from_ndc` twice and building ray arrays per call. It runs
for each mouse-move event over a wire in the wire-layout tool, so the cost is
O(segments) per event. Wires typically have few segments, so this is fine. The
same segment walk is repeated by `Wire._segments` callers (see `wire.md`), so if
segment transforms are cached there, this walk can share the cache.
