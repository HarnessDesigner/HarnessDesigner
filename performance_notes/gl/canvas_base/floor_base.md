# harness_designer/gl/canvas_base/floor_base.py

## Line 16-65 (`FloorBase`) — abstract base, no hot-path work of its own
`__init__` stores the canvas and config. `_initialize_grid`, `set` and `render` all raise `NotImplementedError`; the real work is in the 3D, pegboard and schematic floor subclasses (see their notes). Nothing here runs per frame.

The `render` docstring says the shader program is the `ShaderProgram()` singleton. It is actually one instance per canvas (see `shaders/shader_program.md`). The docstring should be corrected; the behaviour is unaffected.
