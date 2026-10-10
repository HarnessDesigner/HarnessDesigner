# harness_designer/shapes/mesh_cache.py

## Line 39-64 (`load`) — reads a compressed NumPy archive from disk
Opens and reads a `.npz` file for a named primitive. Runs once per primitive per process start, when the primitive is first needed. Compressed archives trade CPU for disk; for small primitives this is fine.

## Line 67-96 (`save`) — writes the archive
Writes the packed mesh and its bounds to disk. Runs once per primitive, after it is built.

**Typing (fixed in this pass):** `extra` is `np.ndarray | None`. `load` returns the five-part tuple or `None`.
