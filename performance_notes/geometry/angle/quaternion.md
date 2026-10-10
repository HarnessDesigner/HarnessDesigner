# harness_designer/geometry/angle/quaternion.py

The module has 35 small methods and no Python loops. Each one does a few numpy operations on a 4-element array, so the cost per call is dominated by numpy call overhead and by allocating a new `Quaternion` for each result. Nothing here runs per frame on its own. It runs whenever an `Angle` is converted or composed, which happens on drag and rotation handlers.

Candidate, only if profiling shows `Quaternion` operations high in a drag: do the composition in place on a preallocated array instead of allocating a new object per call. Not profiled.

Status: static read of the code only. Nothing here has been profiled.
