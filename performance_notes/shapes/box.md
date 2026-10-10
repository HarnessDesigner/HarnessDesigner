# harness_designer/shapes/box.py

## Line 48-83 (`create`) — vertex and face arrays for a box
Builds a small fixed mesh with NumPy. Runs once per primitive, through `cache_primitives`. Fine.

**Typing (fixed in this pass):** `width`, `height`, `depth` are `float`; returns `tuple[np.ndarray, np.ndarray]`.
