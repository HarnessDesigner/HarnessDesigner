# harness_designer/gl/canvas_pegboard/floor.py

## Line 34-43 (`_build_quad`) — per-frame quad rebuild
Builds a 12-float array from Python floats on each call. It is called from `render` every frame (line 162), so each frame allocates a new NumPy array even when the camera has not moved.

## Line 101-124 (`Floor._current_spacing`) — `math.log2` and `2.0 ** n` per frame
Cheap, two floating-point operations. Not worth changing.

## Line 126-178 (`Floor.render`) — per-frame CPU work and buffer upload
Every frame:
- reads camera distance and focal position, and computes the four bounds;
- rebuilds the quad with `_build_quad` (see above);
- uploads it with `glBufferSubData` (the buffer is created with `GL_DYNAMIC_DRAW`);
- sets `projection`, `spacing`, `world_per_pixel`, `dot_color` uniforms.

The upload is small (48 bytes) and the uniform writes are few, so this is light. The easy win is skipping the rebuild and upload when `left/right/bottom/top` have not changed since the last frame.

## Line 77-99 (`Floor.set`) — same teardown-and-rebuild shape as the 3D floor
Rebuilds the VAO and VBO on every toggle. Low frequency, so minor.
