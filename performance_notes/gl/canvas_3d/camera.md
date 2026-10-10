# harness_designer/gl/canvas_3d/camera.py

## Line 17-42 (`build_lookat_matrix`) — 4x4 NumPy matrix per call
Called once per frame from `Canvas._set_view`, and again from `Camera.set` after every move. Allocates a 4x4 matrix and sets 12 elements, plus one `np.cross` and two `np.dot`. Small, but per frame while the camera moves.

## Line 58-83 (`Camera.MoveRigTo`) — per-move arithmetic and one event
Converts the target to float64, subtracts the current position, moves both points, and sends one walk event. Runs per user move, not per frame. Fine.

## Line 86-124 (`Camera.set`) — matrix rebuild on move
Only rebuilds the view matrix if the camera is dirty. Good. Its docstring explains why it is called synchronously from hover handling; that call path can run several times per mouse move, and each rebuild costs one `build_lookat_matrix`. Acceptable.
