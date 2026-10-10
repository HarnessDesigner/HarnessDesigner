# harness_designer/bounds/obb.py

## `_vectorized_ray_test` - per mouse move, per view
One vectorised pass over the three edge axes of every row. Each edge does a norm, a few `np.where` calls and a dot product over the N rows. This is the first pass of every pick (`find_object`), so it runs on every move while a snap or hover is active. The shape is right. Nothing here is a clear saving without a measurement.

Candidate only if picking shows up in a profile: the `edge` norms and axes depend only on the stored corners, so they could be stored per row when the corners change in `update`, and the ray test would then skip recomputing them on every move.
