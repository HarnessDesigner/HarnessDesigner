# harness_designer/handlers/handler_base.py

## Line 55-101 (`obb_face_direction`, `euler_from_matrix_continuous`) — small matrix work
A unit-vector computation and an Euler conversion with at most a few `while` iterations per axis. Runs once per placement or rotation step. Fine.

## Line 105-171 (`set_angle_from_housing`) — rotated OBB corners per accessory placement
Reads `acc_obj.db_obj.part` and builds the rotated OBB corners with a list comprehension of eight NumPy products. Runs once per placement, not per frame. The `part` read is a property access; reading it once into a local (as the function already does, `part = ...`) is correct.

## Line 175-239 (`set_angle_from_cavity`) — same shape as `set_angle_from_housing`
Runs once per placement. Fine.

## Line 275-293 (`reset_angle`) — one assignment
Fine.

## Line 296-353 (`capture_position`, `hover`, `release_capture`, `cancel`, `finalize_at_last_point`) — the hot hooks
`hover` is the per-mouse-move hook. Each concrete handler overrides it (see the per-handler notes). The base class version is a no-op, so the base contributes no cost. `capture_position` stores a point and nothing else.
