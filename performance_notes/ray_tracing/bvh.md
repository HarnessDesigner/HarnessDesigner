# harness_designer/ray_tracing/bvh.pyx

The BVH builder (`FastBVHBuilder`, `calculate_centroids_parallel`, `apply_transform_parallel`), compiled with `boundscheck=False`, `wraparound=False`, `cdivision=True`, `nonecheck=False`. It builds the one tree `kernel.cl` traverses.

## `calculate_centroids_parallel`, `build` — parallel above a size threshold
Centroids are computed with OpenMP `prange` once there are at least `PARALLEL_MIN_PRIMITIVES = 20000` triangles, and `build` splits the tree at depth `PARALLEL_SPLIT_DEPTH = 6` across a `ThreadPoolExecutor` (at most `cpu_count()` workers) with the GIL released. Below the threshold the thread startup would cost more than the work. `count_nodes` sizes the node arrays in advance so no reallocation happens during the build.
A BVH node is 6 floats of bounds and 4 ints (40 bytes); with a leaf threshold of 4 there are about 2n/4 nodes for n triangles, so the tree is about 20 bytes per triangle, small next to the 36 + 36 bytes of triangle data per triangle (`scene.md`).
