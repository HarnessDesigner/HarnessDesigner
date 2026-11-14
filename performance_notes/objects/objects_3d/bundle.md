# harness_designer/objects/objects_3d/bundle.py

`Bundle.render` is now `_render_tubes` (see `objects/mixins/tube.md`), so the per-segment render costs described before no longer apply. The geometry findings are the same as for the 3D wire (see [wire.md](wire.md)).

## Line 513-548 (`_recalculate_geometry`) — bounds computed twice per path change (still)
`self._scale.z = total_length` (line 534) already triggers `_compute_obb` / `_compute_aabb` through the scale callback, and lines 547-548 compute them again. Remove the trailing calls, as was done for `objects_pegboard/wire.py` and `objects_pegboard/bundle.py`.

## Line 581-661 (`_compute_obb`, `_segment_world_corners`), 664-684 (`hit_test_step3`), 750-771 (`_rotation_from_direction`)
Same Angle-per-segment cost (about 130 us per `Angle.from_axis_angle`) and the same full-mesh transform per segment on a pick as in the wire.

## Line 699-746 (`render_selected_overlay`, `_render_waypoint_layouts`) — per frame while selected
One overlay render per segment plus the layout markers; bounded by the number of selected bundles.
