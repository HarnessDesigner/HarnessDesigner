# harness_designer/gl/vbo.py

## Line 679-724 (`VBOHandlerBase.render`) — per-draw uniform work, a string round-trip, and an unconditional hasattr
- Line 706 used to call `hasattr(type(program), "normal_mode")` on every draw. It now reads `program.has_normal_mode`, a class flag, so the probe is gone. The per-draw cost of the check is now a single attribute read.
- Line 714 builds the rotation uniform as `[float(str(v)) for v in angle.as_quat_numpy.tolist()]`. That converts each float to a string and back, four times per draw. `angle.as_quat_numpy` is already a float array, so the uniform can take it directly (or `tuple(map(float, ...))` if a plain list is needed). This is pure waste on the hot draw path.
- Lines 713-715 write `position`, `rotation`, and `scale` uniforms on every draw. Consecutive draws of the same mesh with the same transform (or repeated draws of one object's passes) rewrite identical values. A per-program last-written cache would skip the redundant `glUniform` calls.
- Lines 722-724 bind the VAO and draw. That is one bind, one draw, and one unbind per call, which is the expected cost for an unbatched draw. Batching meshes that share a program is the only larger gain, and it is a change to the callers, not this method.
