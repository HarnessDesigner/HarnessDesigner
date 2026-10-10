# harness_designer/gl/shaders/compiler.py

## Line 7-21 (`compile`) — no caching, but only called at canvas start-up
`compile` calls `glCreateShader`, `glShaderSource`, `glCompileShader` and a status query for every shader. It is called only from the `compile_program` functions in each shader subpackage, which run once per canvas from `ShaderProgram.__init__`. That is a one-time cost per canvas, so it is not on the frame path.

Shader source is read from disk on each `compile_program` call (see the `shaders/*/*.md` notes). The source text is identical across canvases, so a module-level cache of the source strings would save the file reads when the three canvases start. The GL objects themselves cannot be shared between contexts (see `shader_program.md`), so the compile step stays per-context.
