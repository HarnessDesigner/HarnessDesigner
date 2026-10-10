# performance_notes/bounds

Covers `harness_designer/bounds/` (`array_pool.py`, `aabb.py`, `obb.py`, `segment_pool.py`, `manager.py`). The `__init__.py` file has no code.

The main per-move path is `ArrayPool.hit_test` through `gl.object_picker.find_object`. The main load-time cost is the linear `_refs` scan in `ArrayPool.__getitem__`. See [array_pool.md](array_pool.md).
