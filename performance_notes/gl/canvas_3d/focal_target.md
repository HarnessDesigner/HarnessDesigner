# harness_designer/gl/canvas_3d/focal_target.py

## Line 32-52 (`FocalTarget.__init__`) — three presentation objects per canvas
Creates three view objects (schematic, 3D and pegboard). Construction-time only.

## Line 71-92 (`FocalTarget3D.__init__`) — sphere VBO created per instance
`_sphere.create_vbo()` runs for each `FocalTarget3D` constructed. Each canvas makes one focal target, so this is one sphere mesh per canvas. If the sphere mesh is identical across canvases, it could be cached, but the VBO is GL-context-specific (see `shaders/shader_program.md`), so it cannot be shared across canvases.

**Config source note:** `Config = _config.Config.editor_3d` (line 22) is read directly for `focal_target.radius` (line 86), while the colour comes from `canvas.config.focal_target.color` (line 82). The two come from different config objects. This may be intentional, but it means the radius ignores the canvas's own config. Flag for review.
