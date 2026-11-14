# harness_designer/bounds/__init__.py

Facade: re-exports `Manager`, `View`, `AABB`, `OBB`, `SegmentPool` and the two tag constants. No per-call cost. Import time only (it imports `array_pool`, which imports numpy).
