# harness_designer/gl/culling/culling.pyx

Cython frustum culling: `aabb_in_frustum_nogil` (a `nogil` C function over raw float pointers) called from `cull_batch` per worker, and `CullingWorker` threads fed through `Queue(maxsize=1)`. Compiled with `boundscheck=False` and `wraparound=False`; hot loops are in C.

## `cull_batch` — per frame, per worker
Each frame the pool hands slices of the object rows and the frustum planes (a 2D float memoryview, no copy) to its workers, which test every box in C (six plane tests per box, no GIL). The work is O(objects) of C arithmetic, well under a millisecond even for tens of thousands of objects; the surrounding cost is the handoff, one `queue.put` and one `queue.get` per worker per frame (10 workers). For a scene with few objects that handoff is likely larger than the culling itself (measure before deciding): running the culling inline on the calling thread for small counts would remove the thread traffic, and the pool only pays off when the object count is large. Memory: ten persistent threads, each a stack reservation (about 1 MB of address space on Windows, committed memory far smaller).
