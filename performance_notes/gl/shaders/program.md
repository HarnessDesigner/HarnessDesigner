# harness_designer/gl/shaders/program.py

## Line 355-807 (uniform property setters) — every setter is a direct glUniform call with no dirty check
Each setter (for example `render_mode` at line 357 and `view` at 373) calls a `glUniform*` function straight away. The properties are written from the render loop (see `canvas_base/canvas_base.md` and `vbo.md`), so the same value can be written many times per frame. A last-value cache on each property, checked before the GL call, would remove the redundant calls. The matrix setters (`projection`, `view`) are the most valuable to cache because they are written every frame.

## Line 355-807 — getter bodies are `raise NotImplementedError`
The getters raise, so the properties are write-only from the caller's point of view. That is intentional for uniform setters, but it means any `hasattr`/`getattr` probe on these properties depends on the setter rather than the getter. Noted for the getattr review, not a performance issue.
