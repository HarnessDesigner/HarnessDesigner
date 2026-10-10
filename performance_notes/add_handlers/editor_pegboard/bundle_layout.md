# harness_designer/add_handlers/editor_pegboard/bundle_layout.py

## `hover` and `_finalize` - per move
Both call `closest_point_on_chain`, a Python loop over the bundle's chain segments, on every move. For a long chain this is a per-move Python loop. Candidate: vectorise the segment projection over all segments in one numpy call, as `SnapPool.query_ray` does. Needs a measurement with a realistic segment count.
