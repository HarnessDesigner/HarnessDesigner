# harness_designer/gl/shaders/texture/texture.py

## Line 28-51 (`compile_program`) — one-time compile per canvas
Two unclosed file reads, two compiles and a link, run once per canvas start-up. Not on the frame path. Same note as `edges.md` about closing the file handles.

The module docstring says the texture is uploaded from a QImage each time the peg-board table's content changes. That upload is outside this file and is covered by the `objects/objects_pegboard` notes, not here.
