# harness_designer/shapes/rectangle.py

## Line 86-145 (`create_based`, `create`) — vertex and face arrays for a rectangle
Two small builders for a flat rectangle. Each runs once per primitive. Fine.

**Typing (fixed in this pass):** `width` and `height` are `float`; both return `tuple[np.ndarray, np.ndarray]`.
