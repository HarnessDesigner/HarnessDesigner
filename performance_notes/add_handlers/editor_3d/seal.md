# harness_designer/add_handlers/editor_3d/seal.py

## `snap_pool` property - rebuilt on every hover
Same pattern as [cover.py](cover.md), with more work per item. For each snap target it computes a cavity midpoint with numpy (the `cavity_midpoint` math) or reads a position, then builds a new `SnapPool`. Candidate: cache the pool for the session. The snap targets are fixed when the session starts.

## `hover` - per move
Calls `snap_pool.query_ray` (vectorised) and, on a snap change, the angle helpers. Only the free-floating fallback calls `get_position_on_focal_plane`.

## `cavity_plug_search_params` - small helper
Builds a `SearchParameters` once per call. Not on a hot path.
