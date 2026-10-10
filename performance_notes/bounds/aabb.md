# harness_designer/bounds/aabb.py

## `_vectorized_ray_test` - per mouse move, per view
One vectorised slab test over every row, with a Python loop over only the three axes. The cost is linear in the row count and the operations are numpy array ops, so it is the right shape. No change.

## `extent` - copies the live rows on each call
`extent` takes `snapshot_live()`, converts the copy to float64 with `astype`, and then runs `isfinite` and `any` over the whole array before taking min and max. That is a full copy and several full passes for each call.
Candidate: only compute it when the extent is needed, or cache it and invalidate on `update`. Check which caller uses it and how often before changing it. This is not on the mouse-move path.
