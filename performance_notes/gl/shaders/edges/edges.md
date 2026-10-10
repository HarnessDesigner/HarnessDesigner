# harness_designer/gl/shaders/edges/edges.py

## Line 12-39 (`compile_program`) — file reads and compile on every canvas start-up
Reads three shader files with `open(...).read()`, compiles three shaders and links them. This runs once per canvas (from `ShaderProgram.__init__`), so it is a start-up cost only. The three `open` calls are never closed explicitly and rely on garbage collection to release the handles; a `with` block would release them promptly. This does not affect frame time.
