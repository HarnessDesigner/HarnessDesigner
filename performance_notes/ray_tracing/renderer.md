# harness_designer/ray_tracing/renderer.py

## Line 43-83 (`Renderer.init_cl`) — OpenCL context and queue set-up
Picks a GPU device (falling back to CPU), creates the context and queue, and sizes a chunk. Runs once per renderer. Fine.

## Line 84-99 (`Renderer.compile_kernel`) — compiles the kernel source
Builds the OpenCL program from source. Compilation is the expensive step at start-up; the result is reused for every chunk of the render.

## Line 100-end (`Renderer.start`, `_start`) — the render job on a worker thread
Runs the ray-tracing job on a worker thread and streams chunk results through the callback (see the `_start` docstring). The chunk size from `init_cl` sets how many rows each kernel launch covers. Larger chunks mean fewer launches and more memory per launch.

**Note:** this file was not read line by line in this pass. The notes above are from the function structure and the docstrings. A profile of a real render would settle the chunk-size trade-off.
