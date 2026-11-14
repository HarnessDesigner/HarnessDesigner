# harness_designer/objects/objects_pegboard/section.py

A concentric cross-section widget shown on the peg board as a textured quad. The widget is drawn to a texture; the board draws the quad.

## Line 500-550 (`_regrab_texture`), 269-272 (`refresh`) — a full widget grab and a full texture upload per refresh
`refresh` grabs the widget (`grab_rgba`, a Qt render to an RGBA image) and uploads it with `glTexImage2D` plus four `glTexParameteri` calls, every time the section's content changes. `glTexImage2D` re-specifies the texture storage each time; `glTexSubImage2D` can reuse it when the size did not change, and the parameters need only be set once at creation. Memory: the texture is `width x height x 4` bytes at `print_factor` scale; a section grabbed at a high print factor can be several MB per section, plus the transient grab image in system memory. Keeping the grab at the lowest factor that is legible, and releasing the CPU copy right after the upload (it already goes out of scope), is the memory lever.

## Line 571-616 (`render`) — per frame: texture bind, one quad
Binds the texture, sets five uniforms on the texture program and draws one quad. The `mark_visible` writes and the render-id increment are cheap. `_render_connectors` (line 464) temporarily swaps `_vbo`, `_position`, `_angle`, `_scale` and `_material` on the object and calls `super().render` per connector, so each connector costs a full render call; with a few connectors per section that is fine.

## Line 393-403 (`_release_connectors`)
Loops to free connector objects on a rebuild. Not per frame.
