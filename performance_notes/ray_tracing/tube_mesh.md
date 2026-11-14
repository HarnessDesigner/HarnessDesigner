# harness_designer/ray_tracing/tube_mesh.py

Builds the mesh of a conductor for the ray tracer (rounded corners, twist, mitres, smooth normals), from the same plan the viewport draws. Called from `TubeMixin.ray_trace_meshes` on the GUI thread when a scene is built (`Scene.add_object`).

## Line 97-150 (`_piece_grid`), 59-94 (`_around_angles`), 174-203 (`conductor_mesh`) — NumPy, one pass per piece
Each is a handful of vectorised NumPy calls (six allocations and several array operations per piece) with a Python loop over pieces. The cost is linear in the pieces, a few hundred microseconds per piece, once per render. A long, finely bent wire (hundreds of pieces) is tens of milliseconds, and all wires together are the GUI-thread wait before the render starts.

## Memory
Every conductor becomes explicit triangles (`sides x pieces x 2`), non-indexed, at 72 bytes per triangle including normals, so a project with thousands of wires adds tens of MB. See `scene.md` for the non-indexed layout.
