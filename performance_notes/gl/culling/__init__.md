# harness_designer/gl/culling/__init__.py

## Line 32-48 (`__CullingLoader.cull`) — per-frame dispatch to a thread pool
Each frame submits the four object-data lists and frustum data to `CullingThreadPool.cull`. The pool exists so the culling math runs off the GUI thread, which is the right design. The per-frame cost is the submission and the result gathering; the frustum and object arrays are passed by reference, so no copy is made here. No change recommended without measuring.
