# harness_designer/utils/bounding_boxes.py

## Line 10-25 (`compute_aabb`) — min and max over the vertex array
Two NumPy reductions, then wraps the two corners as `Point`s. Called once per model load and per object. Fine.

## Line 26-54 (`compute_obb`) — eight corners from two points
Builds the eight corners of the box in one `np.array` call. Fine.

## Line 55-65 (`adjust_aabb`) — min and max over an array of corners
Two reductions. Fine.
