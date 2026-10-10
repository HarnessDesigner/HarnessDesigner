# harness_designer/gl/shaders/floor/floor.py

## Line 12-36 (`compile_program`) — one-time compile per canvas
Two unclosed file reads, two compiles and a link, run once per canvas start-up. Not on the frame path. Same note as `edges.md` about closing the file handles.
