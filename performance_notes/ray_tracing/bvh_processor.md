# harness_designer/ray_tracing/bvh_processor.py

## Line 46-169 (`BVHWorkerThread`) — one worker thread per BVH job slot
Pulls objects from a shared queue, builds each object's BVH with the compiled `bvh_fast` module, and pushes the result onto a results queue. The module imports `bvh_fast` at the top, so the package cannot be imported until that extension is built (see the note in `__init__.md`).

## Line 170-290 (`ThreadedBVHProcessor`) — a pool of worker threads
Starts `num_threads` workers (default 10, line 174) and joins them on shutdown. Each worker runs the BVH build for whole objects. Ten threads compete for the GIL during any Python-level work, so the speed-up depends on how much of the build runs inside the compiled module.

**Note:** this file was not read line by line in this pass. The notes above come from the class structure. The thread count and the GIL split should be measured on a real scene before tuning.

**Typing (fixed in this pass):** the `typing` aliases (`List`) are replaced with builtins; `__exit__` takes the standard exception types.
