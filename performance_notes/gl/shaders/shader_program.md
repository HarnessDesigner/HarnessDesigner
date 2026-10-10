# harness_designer/gl/shaders/shader_program.py

## Line 18-24 (`ShaderProgram.__init__`) — six program objects per canvas, no process-wide cache
Each canvas builds its own `ShaderProgram`, which creates six program wrappers (grid, faces, edges, vertices, floor, texture). The docstring explains why there is no process-wide cache: each canvas has its own non-shared GL context, and program ids are only valid in the context that created them. So the duplicate compile per canvas is required for correctness, not an oversight. The cost is paid once per canvas at start-up.
